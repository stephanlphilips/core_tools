from dataclasses import dataclass, field
import time

import threading
from queue import PriorityQueue


@dataclass(order=True)
class ExperimentJob:
    priority: float
    job: any = field(compare=False)
    seq_nr: int = 0

    def __post_init__(self):
        # NOTE: use seq_nr to keep insertion order for jobs with equal priority
        self.seq_nr = ExperimentJob.seq_cntr
        ExperimentJob.seq_cntr += 1

    def kill(self):
        self.job.abort_measurement()


# NOTE: use seq_cntr to keep insertion order for jobs with equal priority
ExperimentJob.seq_cntr = 0


class queue_mgr():
    __instance = None
    __init = False

    def __new__(cls):
        if queue_mgr.__instance is None:
            queue_mgr.__instance = object.__new__(cls)
        return queue_mgr.__instance

    def __init__(self):
        if self.__init is False:
            print('Starting job queue_mgr')
            self.q = PriorityQueue()
            # Note: We have to use a dict, because the ExperimentJob only compares on priority
            self.job_refs = dict()

            def worker():
                while True:
                    n_jobs = self.q.qsize()
                    if n_jobs != 0:
                        job_object = self.q.get()
                        print(f'{n_jobs} items queued. Starting next job')
                        try:
                            job_object.job.run()
                        except Exception as e:
                            print(f'{type(e).__name__} {e} in job. Continuing with next job.')
                            print(e)
                        finally:
                            self.q.task_done()
                            try:
                                del self.job_refs[id(job_object)]
                            except KeyError:
                                pass
                    else:
                        # 200ms sleep.
                        time.sleep(0.2)

            self.worker_thread = threading.Thread(target=worker, daemon=True).start()
            self.__init = True

    def put(self, job):
        '''
        put a job into the measurement queue

        Args:
            job (ExperimentJob) : job object
        '''
        self.q.put(job)
        self.job_refs[id(job)] = job

    def kill(self, job):
        '''
        kill a certain job that has been submitted to the queue

        Args:
            job (ExperimentJob) : job object
        '''
        job.kill()

    def killall(self):
        '''
        kill all the jobs
        '''
        job_refs = self.job_refs.copy()
        for job in job_refs.values():
            job.kill()

        self.job_refs = dict()
        print(f'Killed {len(job_refs)} jobs')

    def join(self):
        self.q.join()

    @property
    def n_jobs(self):
        return self.q.qsize()
