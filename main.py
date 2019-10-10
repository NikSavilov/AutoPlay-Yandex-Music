import os
import re
import shutil
import subprocess
import threading
import time
import traceback
from datetime import datetime, timedelta
from os.path import isfile

import pygame
import schedule
from pygame import mixer
from yandex_music.client import Client
from yandex_music.exceptions import NetworkError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from settings import *


def cmd_call(cmd):
	try:
		output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
		dec = output.decode('utf-8')
		return dec
	except subprocess.TimeoutExpired:
		print("TimeoutExpired.")
		return ""
	except:
		return ""


def find_all_devices():
	req = "arp-scan --localnet"
	ans = cmd_call(req)
	devices = {}
	for str_ in ans.split("\n"):
		if re.search(
				"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\t",
				str_):
			str_ = str_.split()
			if len(str_) == 3:
				ip, name, mac = str_[0], str_[1], str_[2]
				devices[ip] = {"mac": mac, "name": name}
	return devices


def is_device_in_network(mac):
	req = "arp-scan --localnet"
	ans = cmd_call(req)
	if ans.rfind(mac) >= 0:
		return True
	else:
		return False


class Player:
	client = None
	folder = None
	current_playlist_folder = None
	tracks = []
	current_track_number = 0
	ready = False
	paused = False
	playing = False
	freezed = False

	def __init__(self, downloads_folder, client):
		self.client = client
		self.folder = os.path.join(BASE_DIR, downloads_folder)
		mixer.init()
		pygame.mixer.music.set_volume(0.05)
		self.prepare_playlist()
		threading.Thread(target=self.queue_controller).start()

	def queue_controller(self):
		while True:
			try:
				if mixer.music.get_busy() == 1:
					time.sleep(0.1)
				elif self.ready and self.playing and not self.paused:
					self.current_track_number += 1
					mixer.music.load(self.tracks[(self.current_track_number) % len(self.tracks)])
					pygame.mixer.music.set_volume(0.05)
					mixer.music.play()
			except:
				pass

	def prepare_playlist(self):
		self.ready = False
		folders = os.listdir(self.folder)
		max_date = None
		for folder in folders:
			try:
				folder_date = datetime.strptime(folder, "%Y%m%d")
				if not max_date or folder_date > max_date:
					max_date = folder_date
			except:
				pass
		if max_date:
			self.current_playlist_folder = os.path.join(self.folder, datetime.strftime(max_date, "%Y%m%d"))
			self.tracks = [
				os.path.join(self.current_playlist_folder, f)
				for f in os.listdir(self.current_playlist_folder) if
				isfile(os.path.join(self.current_playlist_folder, f))]
			if self.tracks:
				mixer.music.load(self.tracks[0])
				self.ready = True
		else:
			self.current_playlist_folder = None
			self.tracks = []
			self.ready = False
			self.download_playlist(self.client, DOWNLOADS_FOLDER)

	def resume(self):
		if not self.freezed and self.ready and self.playing and self.paused:
			print("Resumed.")
			self.paused = False
			mixer.music.unpause()
			return True
		else:
			return False

	def pause(self):  # blocks resume
		if not self.freezed and not self.paused and self.playing:
			print("Paused.")
			mixer.music.pause()
			self.paused = True
			return True
		else:
			return False

	def start(self):
		if not self.freezed and self.ready:
			print("Started.")
			self.playing = True
			self.paused = False
			mixer.music.play()
			return True
		else:
			print("Not ready to start.")
			return False

	def stop(self):
		if not self.freezed and self.playing:
			print("Stopped.")
			self.playing = False
			self.paused = False
			mixer.music.stop()
			return True
		else:
			return False

	def polling(self):
		counter = 0
		while True:
			try:
				if is_device_in_network(MAC):
					if not self.playing and not self.paused:
						self.start()
					elif self.playing and self.paused:
						self.resume()
					else:
						counter = 0
				elif counter > 10 and not self.freezed:
					self.pause()
					time.sleep(1)
					counter = 0
				else:
					counter += 1
					time.sleep(1)
					print("Searching for device.({})".format(counter))
				schedule.run_pending()
			except KeyboardInterrupt:
				exit(0)
			except:
				print(traceback.format_exc())

	def download_playlist(self, client_obj, downloads_folder):
		feed = client_obj.feed()
		songs = feed.generated_playlists[0].data.tracks
		date = datetime.now().strftime("%Y%m%d")
		folder = os.path.join(BASE_DIR, downloads_folder, date)
		try:
			os.mkdir(folder)
		except FileExistsError:
			pass
		for i, song in enumerate(songs):
			try:
				print("Downloading: {t}".format(t=song.track.title))
				filename = "{n}_{t}.mp3".format(n=i, t=song.track.title)
				filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in [".", "_"]]).rstrip()
				song.track.download(os.path.join(folder, filename))
				time.sleep(1)
			except NetworkError:
				time.sleep(10)
			except:
				print(traceback.format_exc())

	def delete_playlist(self):
		try:
			boundary_date = datetime.now() - timedelta(days=3)
			folder = os.path.join(BASE_DIR, DOWNLOADS_FOLDER)
			dirs = os.listdir(folder)
			for dir_ in dirs:
				try:
					folder_date = datetime.strptime(dir_, "%Y%m%d")
					if folder_date < boundary_date:
						shutil.rmtree(os.path.join(BASE_DIR, dir_))
				except:
					print(traceback.format_exc())
		except:
			print(traceback.format_exc())

	def wake_me_up(self):
		for i in range(10):
			try:
				if self.ready:
					if self.playing:
						self.resume()
					else:
						self.start()
					self.freezed = True
				else:
					time.sleep(20)
			except:
				time.sleep(5)
				print(traceback.format_exc())

	def unfreeze(self):
		self.freezed = False
		self.pause()

if __name__ == "__main__":
	assert LOGIN and PASSWORD and DOWNLOADS_FOLDER, "SETTINGS ARE NOT CORRECT"
	while True:
		try:
			client = Client.from_credentials(LOGIN, PASSWORD)
			break
		except:
			print(traceback.format_exc())
			time.sleep(30)
	player = Player(DOWNLOADS_FOLDER, client)

	schedule.every().day.at(TIME_OF_DOWNLOAD).do(player.download_playlist, client_obj=client,
												 downloads_folder=DOWNLOADS_FOLDER)
	schedule.every().day.at(TIME_OF_DELETE).do(player.delete_playlist)
	schedule.every().day.at(TIME_OF_PREPARE).do(player.prepare_playlist)

	schedule.every().day.at(TIME_OF_WAKE_UP).do(player.wake_me_up)
	schedule.every().day.at(TIME_OF_WAKE_UP_UNTIL).do(player.unfreeze)
	player.polling()
