"""
Example implementation of InfoGAN
"""
import sys
import numpy as np
import tensorflow as tf

from learn.models.infogan import InfoGAN2
from learn.models.infogan import InfoganDiscriminatorImpl, InfoganPriorImpl, \
    InfoganEncoderImpl, InfoganGeneratorImpl
from learn.train.observers import Logger, InfoganTensorBoard, TensorBoardLossObserver
from learn.train import ModelTrainer
from learn.data_management import SemiSupervisedMNISTProvider
from learn.networks.convnets import EncoderNetwork, SharedNet, DiscriminatorNetwork, \
    BinaryImgGeneratorNetwork
from learn.stats.distributions import Categorical, IsotropicGaussian, Bernoulli


batch_size = 128

if __name__ == "__main__":
    experiment_dir = sys.argv[1]

    meaningful_dists = {'c1': Categorical(n_classes=10),
                        'c2': IsotropicGaussian(dim=1),
                        'c3': IsotropicGaussian(dim=1)
                        }
    noise_dists = {'z': IsotropicGaussian(dim=62)}
    image_dist = Bernoulli()
    prior_params = {'c1': {'p_vals': np.ones((batch_size, 10), dtype=np.float32) / 10},
                    'c2': {'mean': np.zeros((batch_size, 1), dtype=np.float32),
                           'std': np.ones((batch_size, 1), dtype=np.float32)},
                    'c3': {'mean': np.zeros((batch_size, 1), dtype=np.float32),
                           'std': np.ones((batch_size, 1), dtype=np.float32)},
                    'z': {'mean': np.zeros((batch_size, 62), dtype=np.float32),
                          'std': np.ones((batch_size, 62), dtype=np.float32)}
                    }

    prior = InfoganPriorImpl(meaningful_dists=meaningful_dists,
                             noise_dists=noise_dists,
                             prior_params=prior_params,
                             recurrent_dim=None)

    gen_net = BinaryImgGeneratorNetwork(latent_dim=74, image_shape=(28, 28, 1))
    generator = InfoganGeneratorImpl(data_shape=(28, 28, 1),
                                     meaningful_dists=meaningful_dists,
                                     noise_dists=noise_dists,
                                     data_q_dist=image_dist,
                                     network=gen_net,
                                     recurrent_dim=None)

    shared_net = SharedNet(data_shape=(28, 28, 1))

    disc_net = DiscriminatorNetwork(shared_out_shape=(128, ))
    discriminator = InfoganDiscriminatorImpl(network=disc_net)

    enc_net = EncoderNetwork(shared_out_shape=(128, ))
    encoder = InfoganEncoderImpl(batch_size=batch_size,
                                 meaningful_dists=meaningful_dists,
                                 supervised_dist=None,
                                 network=enc_net,
                                 recurrent_dim=None)

    model = InfoGAN2(batch_size=batch_size,
                     data_shape=(28, 28, 1),
                     prior=prior,
                     generator=generator,
                     shared_net=shared_net,
                     discriminator=discriminator,
                     encoder=encoder,
                     recurrent_dim=None)

    from keras.utils import plot_model
    plot_model(model.gen_train_model, to_file='gen_train_model.png')
    plot_model(model.disc_train_model, to_file='disc_train_model.png')

    # provide the data
    data_provider = SemiSupervisedMNISTProvider(batch_size)
    val_x, val_y = data_provider.validation_data()

    # define observers (callbacks during training)
    tb_writer = tf.summary.FileWriter(experiment_dir)
    logger_observer = Logger(model=model, frequency=1)
    tb_observer = InfoganTensorBoard(model=model, tb_writer=tb_writer, frequency=10,
                                     val_x=val_x, val_y=val_y)
    tb_loss_observer = TensorBoardLossObserver(model=model, tb_writer=tb_writer, frequency=10)

    observers = [logger_observer, tb_observer, tb_loss_observer]

    # train the model
    model_trainer = ModelTrainer(model, data_provider, observers)
    model_trainer.train(n_epochs=100)
