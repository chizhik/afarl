import random
import tensorflow as tf
import matplotlib as plt
import time
import sys
import pickle
import numpy as np
from data_simulation import DataSimulate
from network.cnn import CNN
from network.mlp import MLPSmall
from agent.simple_agent import SimpleAgent
from tensorflow.examples.tutorials.mnist import input_data
from collections import Counter
import os

flags = tf.app.flags

flags.DEFINE_string('data_type', 'mnist', 'data set')

# model conf
flags.DEFINE_integer('expand_size', 2, 'expansion of mnist')
flags.DEFINE_integer('n_features', 16, 'feature dimension')
flags.DEFINE_integer('input_dim', 784 + 16, 'input dimension')
flags.DEFINE_integer('embedded_dim', 50, 'embedded set vector dimension')
flags.DEFINE_integer('n_classes', 10, 'num of classes')
flags.DEFINE_integer('memory_size', 100000, 'max size of experience memory')
flags.DEFINE_string('save_dir', 'saved_mnist_simple', 'where to save the trained model')

# train
flags.DEFINE_integer('train_size', 60000, 'num of training samples')
flags.DEFINE_integer('test_size', 2000, 'num of test samples')
flags.DEFINE_integer('batch_size', 100, 'batch size for training')
flags.DEFINE_integer('n_epoch', 3, 'num of epoch')
flags.DEFINE_float('discount', 1, 'reward discount')
flags.DEFINE_string('policy', 'eps_greedy', '[eps_greedy, softmax]')
flags.DEFINE_integer('target_update_freq', 30, 'target Q update')
flags.DEFINE_float('eps_start', 1, 'eps greedy start')
flags.DEFINE_float('eps_end', 0.1, 'eps greedy end')
flags.DEFINE_integer('anneling_steps', 20000, 'anneling steps for eps')
flags.DEFINE_integer('pre_train_steps', 10000, 'totally random policy steps')
flags.DEFINE_boolean('double_q', True, 'double Q')

# QNet
flags.DEFINE_float('r_cost', -0.02, 'cost for feature acquisition')
flags.DEFINE_float('r_correct', 1, 'reward of correct answer')
flags.DEFINE_float('r_wrong', -1, 'wrong anwser penalty')
flags.DEFINE_float('r_repeat', -100, 'acquiring acquired feature penalty')
flags.DEFINE_string('Q_hidden_sizes', '[300, 100, 50]', 'Q-function hidden sizes')
flags.DEFINE_float('max_lr', 0.001, 'maximum learning rate')
flags.DEFINE_float('min_lr', 0.001, 'minimum learning_rate')
# classifier (FFN)
flags.DEFINE_string('clf_hidden_sizes', '[300, 100, 50]', 'classifier hidden sizes')
flags.DEFINE_float('clf_max_lr', 0.001, 'maximum learning rate of clf')
flags.DEFINE_float('clf_min_lr', 0.001, 'minimum learning rate of clf')
# else
flags.DEFINE_boolean('is_train', False, 'do training or not')
flags.DEFINE_boolean('agg', True, 'Using agg or not')
flags.DEFINE_boolean('random_seed', 123, 'Value of random seed')
flags.DEFINE_boolean('verbose', False, 'verbose or not')
conf = flags.FLAGS

#if conf.agg:
#    matplotlib.use('Agg')
#import matplotlib.pyplot as plt

tf.set_random_seed(conf.random_seed)
random.seed(conf.random_seed)


def main(*args, **kwargs):
    conf.clf_hidden_sizes = eval(conf.clf_hidden_sizes)
    conf.Q_hidden_sizes = eval(conf.Q_hidden_sizes)

    run_config = tf.ConfigProto()
    run_config.gpu_options.allow_growth = True

    if conf.data_type == 'cube':
        assert conf.n_features >= 10
        conf.input_dim = conf.n_features * 2
        train_data = DataSimulate(conf.n_features - 10, conf.train_size)
        test_data = DataSimulate(conf.n_features - 10, conf.test_size)
        conf.n_classes = 8
        train_data_features = train_data.dataset
        train_data_labels = train_data.labels
        test_data_features = test_data.dataset
        test_data_labels = test_data.labels

    elif conf.data_type == 'mnist':
        conf.n_features = 16 * conf.expand_size * conf.expand_size
        conf.input_dim = 784 * conf.expand_size * conf.expand_size + conf.n_features
        from tensorflow.examples.tutorials.mnist import input_data
        mnist = input_data.read_data_sets('../MNIST_data', one_hot=True)
        train_data = mnist.train
        test_data = mnist.test
        conf.train_size = train_data.labels.shape[0]
        conf.test_size = test_data.labels.shape[0]
        conf.n_classes = 10
        train_data_features = train_data.images
        train_data_labels = train_data.labels
        test_data_features = test_data.images
        test_data_labels = test_data.labels

    # load data
    # train_data = DataSimulate(5, conf.train_size)
    # test_data = DataSimulate(5, conf.test_size)
    # conf.n_classes = train_data.labels.shape[1]

    with tf.Session() as sess:
        bias_init = tf.constant_initializer(0.1)
        pred_network = MLPSmall(sess=sess,
                                observation_dims=[conf.input_dim],
                                output_size=conf.n_features + 1,
                                hidden_activation_fn=tf.nn.relu,
                                network_output_type='normal',
                                biases_initializer=bias_init,
                                hidden_sizes=conf.Q_hidden_sizes,
                                name='pred_network', trainable=True)
        target_network = MLPSmall(sess=sess,
                                  observation_dims=[conf.input_dim],
                                  output_size=conf.n_features + 1,
                                  hidden_activation_fn=tf.nn.relu,
                                  network_output_type='normal',
                                  biases_initializer=bias_init,
                                  hidden_sizes=conf.Q_hidden_sizes,
                                  name='target_network', trainable=False)

        agent = SimpleAgent(sess,
                      conf,
                      pred_network,
                      target_network=target_network,
                      name='Agent_' + conf.data_type)

        pred_network_var = list(pred_network.var.values())
        target_network_var = list(target_network.var.values())

        tf.variables_initializer(pred_network_var + target_network_var,
                                 name='agentInit').run()

        tf.global_variables_initializer().run()
        if conf.is_train:
            history = agent.train(train_data_features, train_data_labels,
                                  verbose=conf.verbose)
            # plt.figure()
            # plt.plot(range(len(history)), history)
            # if conf.agg:
            #     plt.savefig('history' + time.strftime("%Y-%m-%d-%I:%M", time.localtime()) + '.png')
            # else:
            #     plt.savefig('history' + time.strftime("%Y-%m-%d-%I:%M", time.localtime()) + '.png')
            #     plt.show()
            #     # else:
            agent.test(test_data_features, test_data_labels)
        else:
            agent.test(test_data_features, test_data_labels)


if __name__ == '__main__':
    tf.app.run()
