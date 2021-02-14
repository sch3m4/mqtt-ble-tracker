
class SingleStateKalmanFilter():
	def __init__(self,A,B,C,x,P,Q,R):
		self.__A = A
		self.__B = B
		self.__C = C
		self.__current_state_estimate = x
		self.__current_prob_estimate = P
		self.__Q = Q
		self.__R = R

	def current_state(self):
		return self.__current_state_estimate

	def step(self,control_input,measurement):
		# prediction step
		predicted_state_estimate = self.__A * self.__current_state_estimate + self.__B * control_input
		predicted_prob_estimate = (self.__A * self.__current_prob_estimate) * self.__A + self.__Q

		# innovation step
		innovation = measurement - self.__C * predicted_state_estimate
		innovation_covariance = self.__C * predicted_prob_estimate * self.__C + self.__R

		# update step
		kalman_gain = predicted_prob_estimate * self.__C * 1 / float ( innovation_covariance )
		self.__current_state_estimate = predicted_state_estimate + kalman_gain * innovation

		# eye(n) = nxn identity matrix
		self.__current_prob_estimate = (1 - kalman_gain * self.__C) * predicted_prob_estimate
