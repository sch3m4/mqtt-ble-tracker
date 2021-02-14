
class MovingAverageFilter():
	def __init__(self,window):
		self.__window = window
		self.__data = []

	def step(self,measurement):
		self.__data.append(measurement)
		if len(self.__data) > self.__window:
			self.__data.pop(0)

	def current_state(self):
		return sum(self.__data) / len(self.__data)
