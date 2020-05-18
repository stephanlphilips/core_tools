import threading
import time

class class1():
	def __init__(self,var_obj):
		self.test = var_obj

	def change_var(self,number):
		self.test.blub += number
		print (self.test.blub)

	def printvar(self):
		print(self.test.blub)

class testing(class1):
	"""docstring for testing"""
	def __init__(self):
		self.blub = 2
	
	def init_other_class(self):
		return class1(self)

	# def printvar(self):
	# 	print("test")
# a = testing()
# b = a.init_other_class()
# b.change_var(5)
# c = a.init_other_class()
# c.change_var(5)
# print(a.blub)

a = testing()
a.printvar()
