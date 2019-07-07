import numpy as np
from itertools import count
import random

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.autograd as autograd
from torch.autograd import Variable
from torch.nn import init
from torch.nn import DataParallel
from torch.utils.data import DataLoader

import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import matplotlib.animation
import seaborn as sns
from IPython.display import HTML

import pretrain
from pretrain import *

import pandas as pd

import navigation2
from navigation2 import *

import sklearn
from sklearn.svm import SVC

import scipy
from scipy.spatial import distance
from scipy import signal

def weight_lowrank0(net, trial = 39, rank = 0, descend = True):
    W0 = torch.load('weights_cpu1/rnn_1515tanh512_checkpoint0')['h2h'].data.numpy()
    Wt = torch.load('weights_cpu1/rnn_1515tanh512_checkpoint{}'.format(trial))['h2h'].data.numpy()
    u, s, vh = np.linalg.svd(Wt - W0)
    smat = np.zeros_like(np.diag(s))
    smat[:rank, :rank] = np.diag(s)[:rank, :rank]
    Wper = np.dot(smat, vh)
    Wper = np.dot(u, Wper)
    if descend == True:
        W = Wt - Wper
    else:
        W = W0 +  Wper
    h2h = torch.from_numpy(W)
    net.h2h = nn.Parameter(h2h)
    print ('norm', np.linalg.norm(Wper))
    
    
 # make the shuffled one instead of removing them, try to see what is the given effect  
def weight_lowrank(net, trial = 300, rank = 0, descend = True, rm_remove = False):
        # read initial and learned weight
        W0 = torch.load('weights_cpu/rnn_1515tanh512_checkpoint0')['h2h'].data.numpy()
        Wt = torch.load('weights_cpu/rnn_1515tanh512_checkpoint{}'.format(trial))['h2h'].data.numpy()
        # decomposition
        u, s, vh = np.linalg.svd(Wt - W0)
        smat = np.zeros_like(np.diag(s))
        # truncated first r ranks
        smat[:rank, :rank] = np.diag(s)[:rank, :rank]
        # recontruct the low rank part
        Wper = np.dot(smat, vh)
        Wper = np.dot(u, Wper)
        if descend == True:
            W = Wt - Wper + np.random.permutation(Wper).reshape(Wper.shape[0], Wper.shape[1])
        else:
            W = W0 +  Wperr
        if rm_remove == True:
            W = Wper   
        h2h = torch.from_numpy(W)
        net.h2h = nn.Parameter(h2h)
        print ('norm', np.linalg.norm(Wper))
        if rm_remove == True:
                print ('norm', np.linalg.norm(net.h2h.data.numpy()))   



# attention to noise level, here corresponed to pretraining , so set noise to 1 
def trajectory(game, pos0, reward_control = 0, init_hidden = True, hidden = torch.zeros(512, 512), size = 19, test = 2, limit_set = 32, epsilon = 0):
    game.reset(set_agent = pos0, reward_control = reward_control, size = size, limit_set = limit_set, test = test)
    done = False
    if init_hidden == True:
        game.hidden = game.net.initHidden()
    else:
        game.hidden = hidden.clone()
    hidden0 = game.hidden.clone()
    Hidden = []
    dH = []
    Action = []
    State = []
    Pos = []
    Pos.append(game.agent.pos)
    while not done:
        pos0, state, reward, done = game.step(game.maxplay, epsilon = epsilon, test=True) # Down
        Hidden.append(game.hidden.data.numpy().squeeze())
        dH.append(torch.norm(game.hidden - hidden0))
        Pos.append(game.agent.pos)
        Action.append(np.argmax(game.action.data.numpy()))
        State.append(state)
        hidden0 = game.hidden.clone()
    return Pos, np.array(Hidden), np.array(dH), np.array(Action), np.array(State), reward

def trajectory_empty(pos0, game, Stim, reward_control = 0, action_ = [], e = 0, open_loop = True, init_hidden = True, hidden = torch.zeros(512, 512), context = torch.zeros(1, 38)):
    game.reset(reward_control = reward_control, size = 15)
    done = False
    if init_hidden == True:
        game.hidden = game.net.initHidden()
    else:
        game.hidden = hidden.clone()
    game.action = torch.zeros(1, 4)
    Hidden = []
    Action = []
    Y = []
    X = []
    dH = []
    hidden0 = game.hidden.clone()
    game.agent.pos = pos0 
    stim = game.visible_state 
#     print (game.visible_state)
    y, x = 0, 0
    action = action_
    for stim in Stim:
        if open_loop == True:
            action = game.step_empty(stim = stim, action_ = action_, epsilon = e, open_loop = open_loop, context = context) # Down
        else:
            action = game.step_empty(stim = stim, action_ = action, epsilon = e, open_loop = open_loop, context = context) # Down
        # up 
        if action == 0: y -= 1
        # right
        elif action == 1: x += 1
        # down
        elif action == 2: y += 1
        # left
        elif action == 3: x -= 1
        game.agent.pos = (y, x)
        Y.append(game.agent.pos[0])
        X.append(game.agent.pos[1])
        Hidden.append(game.hidden.clone().data.numpy().squeeze()) # need copy , avoid same adress 
        dH.append(torch.norm(game.hidden - hidden0))
        Action.append(action)
        hidden0 = game.hidden.clone()
    dH = [dh.data.numpy() for dh in dH]
    return (np.array(Y), np.array(X)), np.array(Hidden), np.array(dH), np.array(Action)


def trajectory_room(pos0, game, T_total = 50, reward_control = 0, epsilon = 0, start = []):
    game.reset(set_agent = (start[0], start[1]), reward_control = reward_control, size = game.size)
    done = False
    game.hidden = game.net.initHidden()
    game.action = torch.zeros(1, 4)
    Hidden = []
    Action = []
    Pos = []
    dH = []
    hidden0 = game.hidden.clone()
    game.agent.pos = pos0 
    game.grid.grid[2:game.size + 2, 2:game.size + 2] = 0
    for i in range(T_total):
        pos0, state, reward, done = game.step(game.maxplay, epsilon = epsilon, test=True)
        Pos.append(game.agent.pos)
        Hidden.append(game.hidden.clone().data.numpy().squeeze()) # need copy , avoid same adress 
        dH.append(torch.norm(game.hidden - hidden0))
        Action.append(np.argmax(game.action.data.numpy()))
        hidden0 = game.hidden.clone()
    dH = [dh.data.numpy() for dh in dH]
    return Pos, np.array(Hidden), np.array(dH), np.array(Action)

class PCA():
    def __init__(self, weight, size = 15, reward_control = 0, epsilon = 1, repetition = 1):
        self.epsilon = epsilon
        self.reward_control = reward_control
        self.weight = weight
        self.game = ValueMaxGame(grid_size = (size, size), holes = 0, random_seed = 4 , set_reward = [(0.5, 0.25), (0.5, 0.75)], input_type = 0, action_control = 1, 
                                 discount = 0.9, alpha = 1, time_limit=100, lam = 0.5)
        self.game.net.load_state_dict(torch.load(self.weight))
        self.size = size
        self.repetition = repetition
    # record hidden activity, attention take test = true
    def record(self, T_duration = None):
        if T_duration == None:
            T_duration = self.size * 4
        self.Hiddens = np.zeros((self.repetition * self.size ** 2, T_duration, 512))
        for k in range(1):
            for j in range (2, self.size):
                for i in range (2, self.size):
                    self.game.reset(set_agent = (j,i), reward_control = self.reward_control, size = self.size)
                    done = False
                    self.game.hidden = self.game.net.initHidden()
                    for t in range(T_duration):
                        pos0, state, reward, done = self.game.step(self.game.maxplay, epsilon = self.epsilon, test = True) # Down
                        self.Hiddens[(j-2) * self.size + (i-2), t] = (self.game.hidden.data.numpy().squeeze())
                        if done == True:
                            self.game.reset(reward_control = self.reward_control, size = self.size)
                            done = False 
    # put every row(time) together into one long trajectory, which means concatenation along rows - number of neurons
    def pca(self, T_duration = None, lowrank = [], descend = True, rm_remove = False):
        if lowrank != []:
            weight_lowrank(self.game.net, rank = lowrank, descend = descend, rm_remove = rm_remove)
        if T_duration == None:
            T_duration = self.size * 4
        self.record(T_duration = T_duration)
        Trajectory = self.Hiddens.reshape(self.repetition * self.size ** 2 * T_duration, 512)
        #  take correlation out
        def minus(a):
            return (a - a.mean())/(a.std() + 1e-5)
        # standarlization along columns which is one specific neural activity trace for all time
        activity = np.apply_along_axis(minus, 1, Trajectory)
        cov = activity.T@activity
        # take eign vector and values
        self.vals, self.vect = np.linalg.eig(cov)
        
    def Dynamics(self, T_total = 200, T_stim = 100, T_duration = 60, Hiddens = [], noise = 2, iters = 4, 
Actions = [2, 0, 1, 3], e = 0,  same = True, legend = False, corner = False, open_loop = True, readout_random = False, h2o = 1) :
        self.Attractors = []
        self.Timescale = []
        self.Trajectory = []
        self.Ys = np.zeros((4, len(Actions), T_total - T_stim))
        self.Xs = np.zeros((4, len(Actions), T_total - T_stim))
        self.Actions = np.zeros((4, len(Actions),  T_total - T_stim))
        self.PCs = np.zeros((4, len(Actions), T_total))
        self.Hiddens = np.zeros((4, len(Actions), T_total - T_stim, 512))
        # take pca for specific game 
        self.Ts = []
        # like starting for different position 
        pos_dict = [('up',(2,9)), ('down', (16,9)), ('left', (9,2)), ('right',(9,16))]
        colors = ['r', 'g', 'b', 'm', 'c']
        k = 0
        # control open loop or not , if open loop false, initialize a h2o with proper gain   
        if readout_random == True and open_loop == False:
            self.game.net.h2o = nn.Parameter(torch.randn(512, 4) * h2o * np.sqrt(2.0/(512+4)))
        # all stimulu actions pairs by two loops 
        for iters1, pos in enumerate(pos_dict):
            for (iters2, action) in enumerate(Actions):
                pos0 = pos[1]
                Stim1 = T_stim * [torch.zeros(9)]
                Stim2 = T_duration * [torch.FloatTensor(self.game.grid.visible(pos0)).resize(9)]
                Stim3 = (T_total - (T_duration + T_stim)) * [torch.zeros(9)] 
                self.Stim = torch.stack(Stim1 + Stim2 + Stim3)
                # trace in empty room 
                Pos1, hidden1, dh1, actions = trajectory_empty(pos0, self.game, self.Stim, action_ = action, e = e, open_loop = open_loop)
                T_transient = np.sum(dh1[T_stim:]>1e-1)
                self.Ts.append(T_transient)
                self.PC_traces = self.vect[:5] @ hidden1.T
                self.PCs[iters1, iters2, :] = self.PC_traces[0, :].copy()
                # record the hidden activity after stimulus 
                self.Hiddens[iters1, iters2, :, :] = hidden1[T_stim:, :]
                # time threshold to assign limit cycle, take it for pwd
                if T_transient > T_total - T_stim  - 1:
                    self.Trajectory.append(self.PC_traces[0][100:])
                self.Ys[iters1, iters2] = Pos1[0][T_stim:]
                self.Xs[iters1, iters2] = Pos1[1][T_stim:]
                self.Actions[iters1, iters2] = actions[T_stim:]
        
    def Dynamics_2clicks(self, T_total = 200, T_stim1 = [20, 3], T_stim2 = [20, 3], wall2 = -1,
                        Hiddens = [], noise = 2, iters = 4, 
action = [0], e = 0,  same = True, legend = False, corner = False, open_loop = True, readout_random = False, h2o = 1) :
        self.Attractors = []
        self.Timescale = []
        self.Trajectory = []
        self.Positions = []
        self.PCs = np.zeros((4, T_total))
        # take pca for specific game 
        self.Ts = []
        # like starting for different position 
        pos_dict = [('up',(2,9)), ('down', (16,9)), ('left', (9,2)), ('right',(9,16))]
        k = 0
        # control open loop or not , if open loop false, initialize a h2o with proper gain   
        if readout_random == True and open_loop == False:
            self.game.net.h2o = nn.Parameter(torch.randn(512, 4) * h2o * np.sqrt(2.0/(512+4)))
        # all stimulu actions pairs by two loops 
        for (iters1, pos1) in enumerate(pos_dict):
            pos1_ = pos1[1]
            if wall2 == -1:
                pos2_ = pos1[1]
            else:
                pos2_ = pos_dict[wall2][1]
            Stim1 = T_stim1[0] * [torch.zeros(9)] + T_stim1[1] *[torch.FloatTensor(self.game.grid.visible(pos1_)).resize(9)]
            Stim2 = T_stim2[0] * [torch.zeros(9)] + T_stim2[1] *[torch.FloatTensor(self.game.grid.visible(pos2_)).resize(9)]
            Stim3 = (T_total - (T_stim1[0] + T_stim1[1] + T_stim2[0] + T_stim2[1])) * [torch.zeros(9)] 
            self.Stim = torch.stack(Stim1 + Stim2 + Stim3)
                # trace in empty room 
            Pos1, hidden1, dh1, actions = trajectory_empty(pos1_, self.game, self.Stim, action_ = action, e = e, open_loop = open_loop)
#                 T_transient = np.sum(dh1[T_stim:]>1e-1)
#                 self.Ts.append(T_transient)
            self.PC_traces = self.vect[:5] @ hidden1.T
            self.PCs[iters1, :] = self.PC_traces[0, :].copy()
                # time threshold to assign limit cycle, take it for pwd
#                 if T_transient > T_total - T_stim  - 1:
#                     self.Trajectory.append(self.PC_traces[0][100:])
            self.Positions.append(Pos1)
                # take the final value of h for mulitple stability
            self.Attractors.append(self.PC_traces[:5, -1])
        self.Attractors = np.array(self.Attractors)
        
## here we need to define a empty room, the network can inside the room with certian feedback given by Wih 
        
    def Dynamics_room(self, T_total = 200, Hiddens = [], iters = 4, e = 0,  readout_random = True, h2o = 1, starts = []):
            self.Attractors = []
            self.Timescale = []
            self.Trajectory = []
            self.Positions = []
            self.PCs = np.zeros((len(starts), T_total))
            # take pca for specific game 
            self.Ts = []
            # like starting for different position 
            pos_dict = [('up',(2,9)), ('down', (16,9)), ('left', (9,2)), ('right',(9,16)), ('empty', (5, 5))]
            colors = ['r', 'g', 'b', 'm', 'c']
            k = 0
            # control open loop or not , if open loop false, initialize a h2o with proper gain   
            if readout_random == True:
                self.game.net.h2o = nn.Parameter(torch.randn(512, 4) * h2o * np.sqrt(2.0/(512+4)))
            # all stimulu actions pairs by two loops 
            for iters, start in enumerate(starts):
                pos0 = start
                # trace in empty room 
                Pos1, hidden1, dh1, actions = trajectory_room(pos0, self.game, T_total = T_total, reward_control = 0, epsilon = 0, start = start)
#                 T_transient = np.sum(dh1[T_stim:]>1e-1)
#                 self.Ts.append(T_transient)
                self.PC_traces = self.vect[:5] @ hidden1.T
                self.PCs[iters, :] = self.PC_traces[0, :].copy()
                # time threshold to assign limit cycle, take it for pwd
#                 if T_transient > T_total - T_stim  - 1:
#                     self.Trajectory.append(self.PC_traces[0][100:])
                self.Positions.append(Pos1)
                # take the final value of h for mulitple stability
#                 self.Attractors.append(self.PC_traces[:5, -1])

def Data_record(weight, k_action = 1, epsilon = 0, size = 15, T = 200, seed_num = 1):
    PC_traces = []
    Hiddens = []
    Poss = []
    Actions = []
    States = []
    Context = []
    for i in range(T):
        torch.manual_seed(np.random.randint(seed_num))
        hidden0 = torch.randn(1, 512)
        c  = np.random.randint(2)
        start = (np.random.randint(2, size +2),  np.random.randint(2, size+2))
        game = ValueMaxGame(grid_size = (size, size), holes = 0, random_seed = 0 , set_reward = [(0.5, 0.25), (0.5, 0.75)], input_type = 0, discount = 0.9, alpha = 1
                           ,lam = 0)
        game.net.load_state_dict(torch.load(weight))
        game.net.k_action = k_action 
        grid = game.grid.grid.copy()
        Pos, hidden, dh, Action, State, reward = trajectory(game, start, reward_control = c, size = size, \
                                                                  test = 0, limit_set = 4, init_hidden = False, hidden = hidden0, epsilon = epsilon)
        Hiddens.append(hidden)
        Poss.append(Pos[1:])
        Actions.append(Action)
        States.append(State)
        Context.append(c * np.ones(len(State)))
    return States, Poss, Hiddens, Actions, Context