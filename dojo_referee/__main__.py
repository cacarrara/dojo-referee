# Copyright (C) 2018 Caio Carrara <eu@caiocarrara.com.br>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# LICENSE for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import argparse
import logging
import logging.config
import tkinter as tk

from dojo_referee.dojo import Dojo, DojoParticipant
from dojo_referee.sound import play_begin, play_finish
from dojo_referee.workers import BlinkingLabelThread, CountdownThread
from dojo_referee import settings

logger = logging.getLogger('dojo_referee')


class ParticipantDialog(tk.Toplevel):
    def __init__(self, master, *args, **kwargs):
        self.dojo = kwargs.pop('dojo')
        self.on_close_callback = kwargs.pop('on_close')

        super().__init__(master, *args, **kwargs)

        self.title('Informe os participantes')
        self.geometry(settings.APPLICATION_GEOMETRY)
        self.resizable(False, False)

        self.setup_widgets()

    def setup_widgets(self):
        self.pilot_var = tk.StringVar()
        self.copilot_var = tk.StringVar()

        self.main_frame = tk.Frame(
            self,
            width=settings.APPLICATION_WIDTH,
            height=settings.APPLICATION_HEIGHT,
            bg='white',
            padx=10,
            pady=5,
        )

        self.pilot_label = tk.Label(
            self.main_frame,
            text='Piloto',
            bg='white',
            padx=5,
            pady=5,
            font=settings.APPLICATION_DEFAULT_FONT,
        )
        self.copilot_label = tk.Label(
            self.main_frame,
            text='Co-Piloto',
            bg='white',
            padx=5,
            pady=5,
            font=settings.APPLICATION_DEFAULT_FONT,
        )

        self.pilot_entry = tk.Entry(
            self.main_frame,
            textvariable=self.pilot_var,
            font=settings.APPLICATION_DEFAULT_FONT,
        )
        self.copilot_entry = tk.Entry(
            self.main_frame,
            textvariable=self.copilot_var,
            font=settings.APPLICATION_DEFAULT_FONT,
        )

        self.save_button = tk.Button(
            self.main_frame,
            text='Save',
            bg='royalblue',
            activebackground='dodgerblue',
            fg='white',
            activeforeground='white',
            font=settings.APPLICATION_DEFAULT_FONT,
            command=self.add_participants_and_close
        )

        self.main_frame.pack(fill=tk.BOTH, expand=1)
        self.pilot_label.pack(fill=tk.X)
        self.pilot_entry.pack(fill=tk.X)
        self.copilot_label.pack(fill=tk.X)
        self.copilot_entry.pack(fill=tk.X)
        self.save_button.pack(fill=tk.X)

    def add_participants_and_close(self):
        pilot_participant = DojoParticipant(self.pilot_var.get())
        copilot_participant = DojoParticipant(self.copilot_var.get())
        self.dojo.add_iteration(pilot_participant, copilot_participant)
        self.destroy()

    def destroy(self):
        if self.on_close_callback:
            self.on_close_callback()
        super().destroy()


class DojoReferee(tk.Tk):
    def __init__(self, args):
        super().__init__()
        self.title(settings.APPLICATION_TITLE)
        self.geometry(settings.APPLICATION_GEOMETRY)
        self.resizable(False, False)
        if args.debug:
            self.clock_str = '00:05'
        else:
            self.clock_str = '{:02}:00'.format(settings.ITERATION_TIME_MIN)

        self.setup_widgets()
        self.protocol('WM_DELETE_WINDOW', self.safe_exit)

        self.dojo = Dojo()
        self.iteration_active = False

    def setup_widgets(self):
        self.main_frame = tk.Frame(
            self,
            width=settings.APPLICATION_WIDTH,
            height=settings.APPLICATION_HEIGHT,
            bg='white',
            padx=10,
            pady=5,
        )
        self.btn_toggle_session = tk.Button(
            self.main_frame,
            text='Start Dojo Session',
            bg='royalblue',
            activebackground='dodgerblue',
            fg='white',
            activeforeground='white',
            command=self.toggle_session,
            font=settings.APPLICATION_DEFAULT_FONT,
        )

        self.btn_toggle_iteration = tk.Button(
            self.main_frame,
            text='Start',
            bg='forestgreen',
            activebackground='green3',
            fg='white',
            activeforeground='white',
            command=self.toggle_iteration,
            font=settings.APPLICATION_SECONDARY_FONT,
            state=tk.DISABLED,
        )

        self.remaining_time = tk.StringVar(self.main_frame)
        self.remaining_time.set(self.clock_str)
        self.countdown_label = tk.Label(
            self.main_frame,
            textvar=self.remaining_time,
            bg='white',
            fg='black',
            font=settings.APPLICATION_HERO_FONT,
        )

        self.main_frame.pack(fill=tk.BOTH, expand=1)
        self.btn_toggle_session.pack(fill=tk.X, pady=10)
        self.countdown_label.pack(fill=tk.X, pady=10)
        self.btn_toggle_iteration.pack(fill=tk.BOTH, pady=10)

    def toggle_session(self):
        if self.dojo.status == Dojo.STARTED:
            self.dojo.finish()
            self.btn_toggle_iteration['state'] = tk.DISABLED
            self.btn_toggle_session['text'] = 'Start Dojo Session'
        else:
            self.dojo.start()
            self.btn_toggle_iteration['state'] = tk.NORMAL
            self.btn_toggle_session['text'] = 'Finish Dojo Session'

    def toggle_iteration(self):
        if self.iteration_active:
            self.finish_iteration()
        else:
            ParticipantDialog(self, dojo=self.dojo, on_close=self.start_iteration)

        self.iteration_active = not self.iteration_active

    def start_iteration(self):
        self.update_remaining_time(self.clock_str)
        self.btn_toggle_iteration['text'] = 'Resume'
        self.btn_toggle_iteration['bg'] = 'orange3'
        self.btn_toggle_iteration['activebackground'] = 'orange2'
        self.countdown = CountdownThread(self, self.clock_str)
        self.countdown.start()
        self.sound_playing = play_begin()

    def finish_iteration(self):
        self.btn_toggle_iteration['text'] = 'Start'
        self.btn_toggle_iteration['bg'] = 'forestgreen'
        self.btn_toggle_iteration['activebackground'] = 'green3'
        self.countdown_label['fg'] = 'black'
        if hasattr(self, 'countdown'):
            self.countdown.stop()
            self.update_remaining_time(self.clock_str)
        if hasattr(self, 'blinking'):
            self.blinking.stop()
        if hasattr(self, 'sound_playing'):
            self.sound_playing.terminate()
        if hasattr(self, 'participant_dialog'):
            self.participant_dialog.destroy()

    def safe_exit(self):
        self.finish_iteration()
        self.after(200, self.destroy)

    def update_remaining_time(self, time):
        if time == '00:00':
            self.btn_toggle_iteration['text'] = 'Stop'
            self.countdown_label['fg'] = 'red'
            self.blinking = BlinkingLabelThread(self, time)
            self.blinking.start()
            self.sound_playing = play_finish()
        self.remaining_time.set(time)


def main():
    logging.config.fileConfig(settings.LOG_CONFIG_FILE)
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', help='activate debug mode', action='store_true')
    args = parser.parse_args()
    referee = DojoReferee(args)
    referee.mainloop()


if __name__ == '__main__':
    main()
