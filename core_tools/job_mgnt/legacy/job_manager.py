import threading as th
import time, logging, importlib, os, time
import inspect
import os
import sqlite3
from datetime import datetime


logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s] (%(threadName)-10s) %(message)s',)

def mk_thread(function):
    def wrapper(*args, **kwargs):
        thread = th.Thread(target=function, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper

class JobManager():
    """For general documentation see presentation on github."""
    def __init__(self):
        # Number of exp run (so one readout is on experiment).
        self.number_of_meas_run = 0
        self.station = None
        # Array with init/readout elements. These arrays contain a dict with an identifier and the readout/init library
        self.init_elements = []
        self.readout_elements = []

        # Array containing the active sequences that can be played.
        self.active_elements = []

        # Array containing all the active calibration routines. Same data structure as for init/readout list.
        self.calib_elements = []

        self.calib_to_run = []
        self.queue = []
        self.__check_for_calibration_routines()
        self.__manage_jobs()

    def add_init_element(self, location):
        # Adds the location where a class that makes the init element can be found. Path can be absolute/relative
        # This can be a file or a directory.
        # Location: str
        # Location: list with type string
        self.init_elements = self.__import_files(location, self.init_elements)

    def add_readout_element(self, location):
        self.readout_elements = self.__import_files(location, self.readout_elements)

    def add_calib_elements(self, location):
        self.calib_elements = self.__import_files(location, self.calib_elements)

    def add_job(self, job):

        # Check job class is correct:

        # add to queue
        self.queue.append(job)


    @mk_thread
    def __check_for_calibration_routines(self):
        # Function that checks if a calibration needs to be done -- called automatically
        self.do_calib = 0

        while self.do_calib < 10:
            lock = th.Lock()
            lock.acquire()

            for i in self.init_elements:
                if i[2].do_calib():
                    self.calib_to_run.append(i[2])

            for i in self.readout_elements:
                if i[2].do_calib():
                    self.calib_to_run.append(i[2])

            for i in self.calib_elements:
                if i[2].do_calib():
                    self.calib_to_run.append(i[2])
            lock.release()
            time.sleep(0.1)
            self.do_calib += 1

    def __import_files(self,location, already_imported):
        # simple function that import files
        # locations list(), type str
        # already import list(), type dict

        # Convert to wanted data type
        if type(location) != list:
            location = [location]

        files_to_load = []

        # Get all python files (if input is a dir).
        for i in location:
            if os.path.isdir(i) == True:
                for file in os.listdir(i):
                    if file.endswith('.py'):
                        files_to_load.append(os.path.splitext(file)[0])
            elif os.path.isfile(i) == True:
                if i.endswith('.py'):
                    files_to_load.append(os.path.splitext(i)[0])
            else:
                print('Error: invalid file given.')

        # import the libraries.
        for file in files_to_load:
            try:
                my_mod = importlib.import_module(file)
            except:
                print(file + " could not be imported")
                continue
            # Check if identifier is there.
            try:
                mod_id = my_mod.identifier
            except:
                print("Error loading the " + file + " module, does this module have no identiefier?")
                continue
            # check if identifier is unique:
            unique = True
            for i in already_imported:
                # print(i[0], mod_id)
                if i[0] == mod_id and i[1] == my_mod:
                    print(file + ".py is already imported.")
                    unique = False
                    break
                elif i[0] == mod_id:
                    print("Identifier of the imported module is not unique,\nin " + i[1].__file__+ " the same identifier is used.")
                    unique = False
                    break

            # Append to array.
            if unique == True:
                already_imported.append((mod_id,my_mod,my_mod.__dict__[mod_id]()))
                print("Imported " + my_mod.__file__)
        return already_imported

    @mk_thread
    def __manage_jobs(self):
        # placeholder for class that contains a thread that does an experiment.
        self.current_job = None
        j = 0
        while j < 10:
            for i in self.calib_to_run[:]:
                # Run only while no meas are running/run while meas in case of a priority_job
                if self.current_job == None:
                    i.calibrate()
                    self.calib_to_run.remove(i)
                elif i.during_exp() == True:
                    self.current_job.pause()
                    i.calibrate()
                    self.calib_to_run.remove(i)
                    self.current_job.resume()

                
            if self.queue:
                self.current_job = self.queue[0]
                self.current_job.start()
            if self.current_job!=None:
                # refreshed after job is done.
                self.number_of_meas_run += self.current_job.get_num_jobs_completed()
                if self.current_job.finished() == True:
                    # Stop all running threads
                    self.current_job = None
                    self.queue.pop(0)

            time.sleep(0.1)
            j+= 1



# a = JobManager()
# a.station = 'mystation'
# a.add_calib_elements('readout_Test.py')
# # a.add_readout_element('readout_Test2.py')
# a.add_init_element('init_test.py')
# # a.add_init_element('.')
