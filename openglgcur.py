"""
implement IRAF gcur functionality

$Id$
"""

import string, os, sys, Numeric
import gwm, wutil, iraf, openglcmd, gki

# The following class attempts to emulate the standard IRAF gcursor
# mode of operation. That is to say, it is basically a keyboard driven
# system that uses the same keys that IRAF does for the same purposes.
# The keyboard I/O will use Tkinter event handling instead of terminal
# I/O primarily because it is simpler and it is necessary to use Tkinter
# anyway.

class Gcursor:

	"""This handles the classical IRAF gcur mode"""

	def __init__(self):
	
		self.x = 0
		self.y = 0
		self.top = None
		self.win = None
		self.markcur = 0
		self.retString = None

	def __call__(self): return self.startCursorMode()

	def startCursorMode(self):
		
		# Get reference to active graphics window and bind event handling
		#  from it.
		self.top = gwm.getActiveWindowTop()
		if not self.top:
			# initialize if graphics hasn't been started yet
			gwm.window()
			gki.kernel.stdgraph.openWS(None,Numeric.array([5,0]))
			gki.kernel.stdgraph.closeWS(None,None)
			self.top = gwm.getActiveWindowTop()
		self.win = gwm.getActiveWindow()
		gwm.raiseActiveWindow()
		self.win.interactive = 1
		self.top.update()
		wutil.focusController.setFocusTo(gwm.getActiveGraphicsWindow())
		if self.win.lastX is not None:
			self.win.activateSWCursor(
				float(self.win.lastX)/self.win.winfo_width(),
				float(self.win.lastY)/self.win.winfo_height())
		else:
			self.win.activateSWCursor()
		self.bind()
		self.win.ignoreNextRedraw = 1
		activate = gki.kernel.getStdout() is None
		if activate:
			gki.kernel.reactivateWS(None,None)
		self.top.mainloop()
		self.unbind()
		self.win.deactivateSWCursor()
		if activate:
			gki.kernel.deactivateWS(None,None)
		self.win.lastX = self.x
		self.win.lastY = self.y
		return self.retString

	def bind(self):
	
		self.win.bind("<Button-1>",self.getMousePosition)
		self.win.bind("<Key>",self.getKey)
		self.win.bind("<Up>",self.moveUp)
		self.win.bind("<Down>",self.moveDown)
		self.win.bind("<Right>",self.moveRight)
		self.win.bind("<Left>",self.moveLeft)
		self.win.bind("<Shift-Up>",self.moveUpBig)
		self.win.bind("<Shift-Down>",self.moveDownBig)
		self.win.bind("<Shift-Right>",self.moveRightBig)
		self.win.bind("<Shift-Left>",self.moveLeftBig)
					
	def unbind(self):
	
		self.win.unbind("<Button-1>")
		self.win.unbind("<Key>")
		self.win.unbind("<Up>")
		self.win.unbind("<Down>")
		self.win.unbind("<Right>")
		self.win.unbind("<Left>")
		self.win.unbind("<Shift-Up>")
		self.win.unbind("<Shift-Down>")
		self.win.unbind("<Shift-Right>")
		self.win.unbind("<Shift-Left>")
		
	def getNDCCursorPos(self):

		"""Do an immediate cursor read and return coordinates in
		NDC coordinates"""

		win = gwm.getActiveWindow()
		sx = win.winfo_pointerx() - win.winfo_rootx()
		sy = win.winfo_pointery() - win.winfo_rooty()
		self.x = sx
		self.y = sy
		# get current window size
		winSizeX = self.win.winfo_width()
		winSizeY = self.win.winfo_height()
		ndcX = float(sx)/winSizeX
		ndcY = float(winSizeY - sy)/winSizeY
		return ndcX, ndcY

	def getMousePosition(self, event):
	
		self.x = event.x
		self.y = event.y

	def moveCursorRelative(self, event, deltaX, deltaY):
		
		gwin = self.win
		# only force focus if window is viewable
		if not wutil.isViewable(self.top.winfo_id()):
			return
		# if no previous position, ignore
		newX = event.x + deltaX
		newY = event.y + deltaY
		if (newX < 0):
			newX = 0
		if (newY < 0):
			newY = 0
		if (newX >= gwin.winfo_width()):
			newX = gwin.winfo_width() - 1
		if (newY >= gwin.winfo_height()):
			newY = gwin.winfo_height() - 1
		wutil.moveCursorTo(gwin.winfo_id(),newX,newY)

	def moveUp(self, event): self.moveCursorRelative(event, 0, -1)
	def moveDown(self, event): self.moveCursorRelative(event, 0, 1)
	def moveRight(self, event): self.moveCursorRelative(event, 1, 0)
	def moveLeft(self, event): self.moveCursorRelative(event, -1, 0)
	def moveUpBig(self, event): self.moveCursorRelative(event, 0, -5)
	def moveDownBig(self, event): self.moveCursorRelative(event, 0, 5)
	def moveRightBig(self, event): self.moveCursorRelative(event, 5, 0)
	def moveLeftBig(self, event): self.moveCursorRelative(event, -5, 0)

	def readString(self, prompt=""):
		"""Prompt and read a string"""
		stdout = gki.kernel.getStdout(default=sys.stdout)
		stdin = gki.kernel.getStdin(default=sys.stdin)
		stdout.write(prompt)
		stdout.flush()
		return stdin.readline()[:-1]

	def getKey(self, event):

		# The main character handling routine where no special keys
		# are used (e.g., control or arrow keys)
		key = event.char
		if not key:
			# ignore keypresses of non printable characters
			return
		x,y = self.getNDCCursorPos()
   		if self.markcur and key not in 'q?:=UR':
		   	metacode = openglcmd.markCross(x,y)
			openglcmd.appendMetacode(metacode)
		if key == ':':
			colonString = self.readString(prompt=": ")
			if colonString[0] == '.':
				if colonString[1:] == 'markcur+':
					self.markcur = 1
				elif colonString[1:] == 'markcur-':
					self.markcur = 0
				elif colonString[1:] == 'markcur':
					self.markcur = not self.markcur
				else:
					print "Don't handle this CL level gcur :. commands."
					print "Please check back later."
			else:
				self._setRetString(key,x,y,colonString)
		elif key == '=':
			# snap command - print the plot
			printPlot()
		elif key in string.uppercase:
			if   key == 'R':
				openglcmd.redrawOriginal()
			elif key == 'T':
				textString = self.readString(prompt="Annotation string: ")
				metacode = openglcmd.text(textString,x,y)
				openglcmd.appendMetacode(metacode)
			elif key == 'U':
				openglcmd.undo()
			else:
				print "Not quite ready to handle this particular" + \
					  "CL level gcur command."
				print "Please check back later."
		else:
			self._setRetString(key,x,y,"")

	def getShiftKey(self, event):

		print event.key
		print ord(event.key)

	def _setRetString(self, key, x, y, colonString):

		wcs = gwm.getActiveWindow().iplot.wcs
		if wcs:
			wx,wy,gwcs = gwm.getActiveWindow().iplot.wcs.get(x,y)
		else:
			wx,wy,gwcs = x,y,0
		if key <= ' ' or ord(key) >= 127:
			key = '\\%03o' % ord(key)
		self.retString = str(wx)+' '+str(wy)+' '+str(gwcs)+' '+key
		if colonString:
			self.retString = self.retString +' '+colonString
		self.top.quit() # time to go!

def printPlot():

	win = gwm.getActiveWindow()
	gkibuff = win.iplot.gkiBuffer.get()
	if gkibuff:
		# write to a temporary file
		tmpfn = iraf.mktemp("snap") + ".gki"
		fout = open(tmpfn,'w')
		fout.write(gkibuff.tostring())
		fout.close()
		try:
			graphcap = gki.kernel.devices
			stdplot = iraf.envget('stdplot')
			printtaskname = graphcap[stdplot]['tn']
			printtask = iraf.getTask(printtaskname)
			# Need to redirect input because running this task with
			# input from StatusLine does not work for some reason.
			# May need to do this for other IRAF tasks run while in
			# gcur mode (if there are more added in the future.)
			printtask(tmpfn,Stdin=sys.__stdin__,Stdout=sys.__stdout__)
		finally:
			os.remove(tmpfn)
	stdout = gki.kernel.getStdout(default=sys.stdout)
	stdout.write("snap completed\n")

