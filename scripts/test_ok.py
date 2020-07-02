from core.utils import set_global_seed
from ok import option_keyboard
from core.value_function import ValueFunction
import argparse
import gym
import envs
import torch
import numpy as np
import os
import pickle

parser = argparse.ArgumentParser('test_ok')
parser.add_argument('-e', '--env-name', default='ForagingWorld-v0',
                    help='Name of environment')
parser.add_argument('-s', '--seed', default=0, type=int,
                    help='Random seed')
parser.add_argument('--exp-name', required=True,
                    help='Name of experiment')
parser.add_argument('--n-test-episodes', default=100,
                    help='Number of test episodes')
parser.add_argument('--visualize', action='store_true',
                    help='Flag for visualization')
parser.add_argument('--saved-models', required=True,
                    help='Path to saved models')
parser.add_argument('--save-path', default='',
                    help='Path to file to which results are to be saved')
parser.add_argument('--w', default=[1, 1], nargs=2, type=int,
                    help='Weight vector')


def main():
    args = parser.parse_args()
    env = gym.make(args.env_name)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    set_global_seed(args.seed)

    d = env.num_resources()
    w = np.array(args.w)
    env.set_learning_options(w=w, flag=True)

    hyperparams_file = open(os.path.join(args.saved_models.split('saved_models')[0],
                            'hyperparams'), 'rb')

    # Loading saved models and constant values
    returns = []
    if args.save_path:
        fp = open(args.save_path, 'a+b')

    hyperparams = pickle.load(hyperparams_file)
    gamma = hyperparams.gamma_ok
    max_ep_steps = hyperparams.max_steps_agent

    value_fns = [ValueFunction(input_dim=env.observation_space.shape[0] + d,
                               action_dim=(env.action_space.n + 1),
                               n_options=d,
                               hidden=[64, 128],
                               batch_size=hyperparams.ok_batch_size,
                               gamma=gamma,
                               alpha=hyperparams.alpha_ok)
                 for _ in range(d)]

    for i in range(env.num_resources()):
        if not torch.cuda.is_available():
            checkpoint = torch.load(os.path.join(args.saved_models,
                                                 'value_fn_%d.pt' %
                                                 (i + 1)),
                                    map_location=torch.device('cpu'))
        else:
            checkpoint = torch.load(os.path.join(args.saved_models,
                                                 'value_fn_%d.pt' %
                                                 (i + 1)))

        value_fns[i].q_net.load_state_dict(checkpoint['Q'])
        value_fns[i].q_net.to(device)

    # Testing
    for _ in range(args.n_test_episodes):
        s = env.reset()
        done = False
        s = torch.from_numpy(s).float().to(device)
        n_steps = 0
        ret = 0

        while not done:
            (s_next, done, _, _, n_steps, info) = option_keyboard(env, s, w,
                                                                  value_fns,
                                                                  gamma,
                                                                  n_steps,
                                                                  max_ep_steps,
                                                                  device,
                                                                  args.visualize)

            ret += sum(info['rewards'])
            s = torch.from_numpy(s_next).float().to(device)

        print('Episode return:', ret)
        returns.append(ret)

    returns = np.array(returns)
    print('Mean: %f, Std. dev: %f' % (returns.mean(), returns.std()))
    pickle.dump({'Seed': args.seed, 'Returns': returns}, fp)
    fp.close()


if __name__ == '__main__':
    main()
