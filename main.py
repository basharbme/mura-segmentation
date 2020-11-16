"""

Predict xray and void sections of an xray image.

Author: Luke Farritor 10/26/20

"""
import pandas as pd
from IPython.display import Image, display
from keras_preprocessing.image import ImageDataGenerator
from tensorflow.keras.preprocessing.image import load_img
import PIL
from PIL import Image as pImage
from PIL import ImageOps
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.python.keras.models import Model
from tensorflow import keras
import tensorflow as tf
from keras.models import load_model
from tensorflow.python.keras.optimizer_v2.adam import Adam
import numpy as np

# setup GPU
config = tf.compat.v1.ConfigProto(gpu_options=
                                  tf.compat.v1.GPUOptions(per_process_gpu_memory_fraction=0.6)
                                  # device_count = {'GPU': 1}
                                  )
config.gpu_options.allow_growth = True
session = tf.compat.v1.Session(config=config)
tf.compat.v1.keras.backend.set_session(session)
gpus = tf.config.experimental.list_physical_devices('GPU')

# variables
csv_name = "images.csv"
num_classes = 2
batch_size = 4
image_size = (512, 512)
validation_set_length = 16


# load image paths from csv file
def get_image_paths():
    return pd.read_csv(csv_name, header=None, index_col=0, squeeze=True).to_dict()


image_paths = get_image_paths()


class ImageHandler(keras.utils.Sequence):
    """Helper to iterate over the data (as Numpy arrays)."""

    def __init__(self, batch_size, image_size, image_paths):
        self.batch_size = batch_size
        self.image_size = image_size
        self.image_paths = image_paths
        self.num_augmentations = 9  # including the normal image

    def __len__(self):
        return (len(self.image_paths) // self.batch_size) * self.num_augmentations

    def __getitem__(self, idx):
        """Returns tuple (input, target) correspond to batch #idx."""
        # i = idx % ((len(self) // self.num_augmentations) // self.batch_size)
        i = (((idx) * self.batch_size) // (self.num_augmentations))
        aug_id = idx % self.num_augmentations
        # aug_id = (idx * self.batch_size) // len(self.image_paths)

        # if(idx == 20):
        print(" " + str(i) + " " + str(idx * batch_size) + " " + str(idx) + " " + str(len(self.image_paths)))

        batch_input_img_paths = list(self.image_paths.keys())[i : i + self.batch_size]
        batch_target_img_paths = list(self.image_paths.values())[i : i + self.batch_size]

        x = np.zeros((self.batch_size,) + self.image_size + (1,), dtype="float32")
        for j, path in enumerate(batch_input_img_paths):
            img = load_img(path, color_mode="grayscale")
            img = self.perform_augmentation(img, aug_id)

            # pad the image to 512
            img_arr = np.array(img)
            img_arr = np.pad(img_arr,
                             ((0, self.image_size[0] - img_arr.shape[0]), (0, self.image_size[1] - img_arr.shape[1])),
                             mode='constant')

            # set the image in the array
            x[j] = np.expand_dims(img_arr / 255, 2)

            # if(i > len(self) / self.num_augmentations):
            # displays the image for debugging
            # print(img_arr[:20,:20])
            # below image eventually saves whole dataset to folder, very helpful for debugging
            if(len(self) == 63):
                pImage.fromarray(x[j][:,:,0] * 255).convert('RGB').save("./test_images/" + str(i) + "_" + str(aug_id) + ".png")
            # pImage.fromarray(x[j][:,:,0], mode="I").save("./test_images")

        y = np.zeros((self.batch_size,) + self.image_size + (1,), dtype="uint8")
        for j, path in enumerate(batch_target_img_paths):
            img = load_img(path, color_mode="grayscale")
            img = self.perform_augmentation(img, aug_id)

            # pad the image to 512
            img_arr = np.array(img)
            img_arr = np.pad(img_arr,
                             ((0, self.image_size[0] - img_arr.shape[0]), (0, self.image_size[1] - img_arr.shape[1])),
                             mode='constant')

            # set the image in the array
            y[j] = np.expand_dims(img_arr / 255, 2)

        return x, y

    def perform_augmentation(self, img, aug):
        if aug == 1:
            # horizontal flip
            img = img.transpose(PIL.Image.FLIP_LEFT_RIGHT)
        if aug == 2:
            # vertical fip
            img = img.transpose(PIL.Image.FLIP_TOP_BOTTOM)
        if aug == 3:
            # horizontal vertical flip
            img = img.transpose(PIL.Image.FLIP_TOP_BOTTOM)
            img = img.transpose(PIL.Image.FLIP_LEFT_RIGHT)
        if aug == 4:
            # 90 degree rotation
            img = img.transpose(PIL.Image.ROTATE_90)
        if aug == 5:
            # 180 degree rotation
            img = img.transpose(PIL.Image.ROTATE_180)
        if aug == 6:
            # 270 degree rotation
            img = img.transpose(PIL.Image.ROTATE_270)
        if aug == 7:
            # horizontal shrink
            img = img.resize((int(img.size[0] / 2), img.size[1]))
        if aug == 8:
            # vertical shrink
            img = img.resize((img.size[0], int(img.size[1] / 2)))

        # img.show()
        return img




def unet(pretrained_weights=None, input_size=(512, 512, 1)):
    inputs = layers.Input(input_size)
    filter_num = 16
    conv1 = layers.Conv2D(filter_num * 1, 3, activation='relu', padding='same', kernel_initializer='he_normal')(inputs)
    conv1 = layers.Conv2D(filter_num * 1, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv1)
    batch1 = layers.BatchNormalization()(conv1)
    pool1 = layers.MaxPooling2D(pool_size=(2, 2))(batch1)

    conv2 = layers.Conv2D(filter_num * 2, 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool1)
    conv2 = layers.Conv2D(filter_num * 2, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv2)
    batch2 = layers.BatchNormalization()(conv2)
    pool2 = layers.MaxPooling2D(pool_size=(2, 2))(batch2)

    conv3 = layers.Conv2D(filter_num * 4, 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool2)
    conv3 = layers.Conv2D(filter_num * 4, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv3)
    batch3 = layers.BatchNormalization()(conv3)
    pool3 = layers.MaxPooling2D(pool_size=(2, 2))(batch3)

    conv4 = layers.Conv2D(filter_num * 8, 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool3)
    conv4 = layers.Conv2D(filter_num * 8, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv4)
    batch4 = layers.BatchNormalization()(conv4)
    drop4 = layers.Dropout(0.5)(batch4)
    pool4 = layers.MaxPooling2D(pool_size=(2, 2))(drop4)

    conv5 = layers.Conv2D(filter_num * 16, 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool4)
    conv5 = layers.Conv2D(filter_num * 16, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv5)
    batch5 = layers.BatchNormalization()(conv5)
    drop5 = layers.Dropout(0.5)(batch5)

    up6 = layers.Conv2D(filter_num * 8, 2, activation='relu', padding='same', kernel_initializer='he_normal')(
        layers.UpSampling2D(size=(2, 2))(drop5))
    merge6 = layers.concatenate([drop4, up6], axis=3)
    conv6 = layers.Conv2D(filter_num * 8, 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge6)
    conv6 = layers.Conv2D(filter_num * 8, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv6)

    up7 = layers.Conv2D(filter_num * 4, 2, activation='relu', padding='same', kernel_initializer='he_normal')(
        layers.UpSampling2D(size=(2, 2))(conv6))
    merge7 = layers.concatenate([conv3, up7], axis=3)
    conv7 = layers.Conv2D(filter_num * 4, 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge7)
    conv7 = layers.Conv2D(filter_num * 4, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv7)

    up8 = layers.Conv2D(filter_num * 2, 2, activation='relu', padding='same', kernel_initializer='he_normal')(
        layers.UpSampling2D(size=(2, 2))(conv7))
    merge8 = layers.concatenate([conv2, up8], axis=3)
    conv8 = layers.Conv2D(filter_num * 2, 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge8)
    conv8 = layers.Conv2D(filter_num * 2, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv8)

    up9 = layers.Conv2D(filter_num * 1, 2, activation='relu', padding='same', kernel_initializer='he_normal')(
        layers.UpSampling2D(size=(2, 2))(conv8))
    merge9 = layers.concatenate([conv1, up9], axis=3)
    conv9 = layers.Conv2D(filter_num * 1, 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge9)
    conv9 = layers.Conv2D(filter_num * 1, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv9)
    conv9 = layers.Conv2D(2, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv9)

    conv10 = layers.Conv2D(1, 1, activation='sigmoid')(conv9)

    model = Model(inputs, conv10)

    model.compile(optimizer=Adam(lr=1e-4), loss='binary_crossentropy', metrics=['accuracy'])

    model.summary()

    if (pretrained_weights):
        model.load_weights(pretrained_weights)

    return model


# expects an np array of size (width, height, 1)
def display_image(img):
    pImage.fromarray(np.uint8(img[:, :, 0] * 255), mode="L").show()


# split our image paths into training and validation image paths
validation_image_paths = dict(list(image_paths.items())[:validation_set_length])
train_image_paths = dict(list(image_paths.items())[validation_set_length:])


# create our image handler classes
train_images = ImageHandler(batch_size, image_size, train_image_paths)
validation_images = ImageHandler(batch_size, image_size, validation_image_paths)

print("LEN  " + str(len(train_images)))

# create our model
model = unet()

callbacks = [
    keras.callbacks.ModelCheckpoint("xray_segmentation.h5", save_best_only=True)
]

# Train the model, doing validation at the end of each epoch.
epochs = 20
model.fit(train_images, epochs=epochs, validation_data=validation_images, callbacks=callbacks)

# other method im trying
# data_gen_args = ImageDataGenerator(
#     horizontal_flip=True,
#     vertical_flip=True,
#     fill_mode='constant',
#     cval=0,
#     rotation_range=360
# )
# xray_datagen = ImageDataGenerator(**data_gen_args)
# mask_datagen = ImageDataGenerator(**data_gen_args)
#
# seed = 1
# xray_datagen.fit(images, augment=True, seed=seed)
# mask_datagen.fit(masks, augment=True, seed=seed)
# xray_generator = xray_datagen.flow_from_directory(
#     'data/images',
#     class_mode=None,
#     seed=seed)
# mask_generator = mask_datagen.flow_from_directory(
#     'data/masks',
#     class_mode=None,
#     seed=seed)

validation_predictions = model.predict(validation_images)
print(validation_predictions.shape)

for i in range(0, len(validation_image_paths)):
    image = pImage.open(list(validation_image_paths.keys())[i])
    image_handler = ImageHandler(1, image_size, {list(validation_image_paths.keys())[i] : list(validation_image_paths.values())[i]})
    prediction = model.predict(image_handler)
    predicted_image = pImage.fromarray(np.uint8(prediction[0][:, :, 0] * 255), mode="L")

    combined_image = pImage.new("I", (image_size[0] * 2, image_size[1]))
    combined_image.paste(image, (0,0))
    combined_image.paste(predicted_image, (image_size[0], 0))
    combined_image.show()
    k = input()