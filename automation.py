#!/usr/bin/env python

from threading import Event, Thread
import datetime
import curses
import traceback
import time
import RPi.GPIO as io
io.setmode(io.BCM)

# IO Pin Definitions
power_pin = 23

# IO Pin Configuration
io.setup(power_pin, io.OUT)
io.output(power_pin, False)

# Global State
power_status = "OFF"
check_status = "NEEDS CHECK"
start_time = time.time()
status_msg = ""
log_msgs = []


# Function Definitions
def datetimestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %X:%M:%S")


def callRepeatedly(interval, func, *args):
    global start_time
    stopped = Event()

    def loop():
        # the first call is in `interval` seconds
        # will repeat every `interval` seconds
        elapsed = (time.time() - start_time)
        while not stopped.wait(interval - (elapsed % interval)):
            func(*args)
    Thread(target=loop).start()
    return stopped.set


def triggerCheck():
    global check_status
    check_status = "NEEDS CHECK"


def powerOn():
    global power_status
    if power_status != "ON":
        io.output(power_pin, True)
        power_status = "ON"
        displayMsg(datetimestamp()+" : POWER ON")


def powerOff():
    global power_status
    if power_status != "OFF":
        io.output(power_pin, False)
        power_status = "OFF"
        displayMsg(datetimestamp()+" : POWER OFF")


def currentEvents(chkDevice, chkType='any'):
    current = []
    now = datetime.datetime.now()
    for event in event_schedule:
        timeText = now.strftime("%d %b %Y ")+event[0]
        evt_time = datetime.datetime.strptime(timeText, "%d %b %Y %H:%M")
        evt_device = event[1]
        evt_command = event[2]
        devMatch = chkDevice == evt_device
        typeMatch = (chkType == evt_command or chkType == 'any')
        afterEarliest = (evt_time + datetime.timedelta(seconds=-5)) <= now
        beforeLatest = now <= (evt_time + datetime.timedelta(seconds=5))
        timeMatch = afterEarliest and beforeLatest
        if (devMatch and typeMatch and timeMatch):
            current.append(event)
    return current


def fromEventList(evtList, chkDevice, chkType='any'):
    outList = []
    for event in evtList:
        evt_time = event[0]
        evt_device = event[1]
        evt_command = event[2]
        devMatch = chkDevice == evt_device
        typeMatch = (chkType == evt_command or chkType == 'any')
        if (devMatch and typeMatch):
            outList.append(event)
    return outList


def listSchedule():
    displayMsg("-- defined events --")
    for event in event_schedule:
        evt_time = event[0]
        evt_device = event[1]
        evt_command = event[2]
        displayMsg("TIME: "+evt_time+"   DEV: "+evt_device+"   CMD: "+evt_command)


def setStatusMsg(msg):
    global status_msg
    status_msg = "-- q=quit | o=turn on | p=turn off | l=list schedule --"
    status_msg += "  |" + msg + "|"


def displayMsg(msg):
    global log_msgs
    log_msgs.append(msg)
    overflow = len(log_msgs) - 18
    if overflow > 0:
        # discard overflow from the front of the list
        log_msgs = log_msgs[overflow:]


def drawScreen():
    screen.clear()
    screen.addstr(status_msg + "\n", curses.A_REVERSE)
    for msg in log_msgs:
        screen.addstr(msg + "\n")
    screen.refresh()


def doMain():
    global check_status

    screen.nodelay(1)  # do not wait for keypresses

    # begin checking event loop
    stop_checking = callRepeatedly(10.0, triggerCheck)

    while True:
        # handle the need to check the time and switch the lights
        if check_status != "DONE":
            displayMsg(datetimestamp()+" : ...CHECKING...")
            current = currentEvents("Verilux")
            if (len(fromEventList(current, "Verilux", "ON")) > 0):
                powerOn()
            if (len(fromEventList(current, "Verilux", "OFF")) > 0):
                powerOff()
            neoPixelSequences = fromEventList(current, "NeoPixel", "SEQ")
#            if (len(neoPixelSequences) > 0):
#                doSequence(neoPixelSequences[0][3])
            check_status = "DONE"
            setStatusMsg(power_status)

        # handle keyboard input
        event = screen.getch()
        if event == ord("q"): break
        elif event == ord("o"): powerOn()
        elif event == ord("p"): powerOff()
        elif event == ord("l"): listSchedule()

        # update the screen
        setStatusMsg(power_status)
        drawScreen()

        # don't hog the cpu
        time.sleep(0.1)

    # stop triggering the timing check
    stop_checking()


###################################################################
# hard code the event times (for now)
event_schedule = [
    ("10:00", "Verilux", "ON")      # local 5am Verilux On
    ,("14:00", "Verilux", "OFF")    # local 9am Verilux Off
    ,("22:00", "Verilux", "ON")     # local 5pm Verilux On
    ,("02:00", "Verilux", "OFF")    # local 9pm Verilux Off
    ]
###################################################################


# Start the application
if __name__ == '__main__':
    try:
        # take Control of the Console
        screen = curses.initscr()

        # configure it like a term
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        screen.keypad(1)

        # start the main loop
        doMain()

        # return control to the console
        screen.keypad(0)
        curses.curs_set(1)
        curses.nocbreak()
        curses.echo()
        curses.endwin()
    except:
        # in case of an exception
        # restore the terminal and report the exception
        screen.keypad(0)
        curses.curs_set(1)
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        traceback.print_exc()
        print "--- type ^Z to return to command line ---"
