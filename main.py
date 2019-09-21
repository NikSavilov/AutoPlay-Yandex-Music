import os
import re
import shutil
import subprocess
import threading
import time
import traceback
from datetime import datetime, timedelta
from os.path import isfile
import asyncio

import pygame
import yandex_music
from pygame import mixer

from yandex_music.client import Client
import schedule
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

	def __init__(self, downloads_folder, client):
		self.client = client
		self.folder = os.path.join(BASE_DIR, downloads_folder)
		mixer.init()
		self.prepare_playlist()
		threading.Thread(target=self.queue_controller).start()

	def queue_controller(self):
		while True:
			try:
				if mixer.music.get_busy() == 1:
					time.sleep(0.1)
				elif ready and not self.paused:
					mixer.music.load(self.tracks[self.current_track_number % len(self.tracks)])
					mixer.music.play()
			except:
				pass

	def prepare_playlist(self):
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
		if self.ready and not self.paused and mixer.music.get_busy() == 0:
			self.start()

	def pause(self):  # blocks resume
		self.stop()
		self.paused = True

	def start(self):
		if self.ready:
			mixer.music.play()

	def stop(self):
		mixer.music.stop()

	def polling(self):
		counter = 0
		while True:
			try:
				if is_device_in_network(MAC):
					self.resume()
					counter = 0
				else:
					counter += 1
					time.sleep(1)
					print("Searching for device.")
					if counter > 10:
						self.stop()
			except:
				print(traceback.format_exc())

	def download_playlist(self, client_obj, downloads_folder):
		feed = client_obj.feed()
		songs = feed.generated_playlists[0].data.tracks
		date = datetime.now().strftime("%Y%m%d")
		folder = os.path.join(BASE_DIR, downloads_folder, date)
		os.mkdir(folder)
		for i, song in enumerate(songs):
			try:
				print("Downloading: {t}".format(t=song.track.title))
				song.track.download(os.path.join(folder, str(i) + ".mp3"))
				time.sleep(1)
			except NetworkError:
				time.sleep(10)
			except:
				print(traceback.format_exc())

	def delete_playlist(self):
		try:
			boundary_date = datetime.now() - timedelta(days=3)
			folder = os.path.join(BASE_DIR, "downloads")
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

	schedule.every().day.at("06:00").do(player.download_playlist, client=client, downloads_folder=DOWNLOADS_FOLDER)
	schedule.every().day.at("06:40").do(player.delete_playlist)
	schedule.every().day.at("06:50").do(player.prepare_playlist)

	player.polling()
