from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential
from keras.layers import Conv2D, MaxPooling2D
from keras.layers import Activation, Dropout, Flatten, Dense
from keras import backend as K
import os, os.path
import numpy as np

img_width, img_height = 150, 150

train_data_dir = 'building_photos/train'
validation_data_dir = 'building_photos/validation'
test_data_dir = 'building_photos/validation'
nb_train_samples = sum([len(files) for r, d, files in os.walk("./building_photos/train")])
nb_validation_samples = sum([len(files) for r, d, files in os.walk("./building_photos/validation")])
nb_test_samples = sum([len(files) for r, d, files in os.walk("./building_photos/test")])
print("nb_train_samples: "+str(nb_train_samples))
print("nb_validation_samples: "+str(nb_validation_samples))
print("nb_test_samples: "+str(nb_test_samples))


epochs = 100
batch_size = 5

if K.image_data_format() == 'channels_first':
    input_shape = (3, img_width, img_height)
else:
    input_shape = (img_width, img_height, 3)

model = Sequential()
model.add(Conv2D(32, (3, 3), input_shape=input_shape))
model.add(Activation('relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))

model.add(Conv2D(32, (3, 3)))
model.add(Activation('relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))

model.add(Conv2D(64, (3, 3)))
model.add(Activation('relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))

model.add(Flatten())
model.add(Dense(64))
model.add(Activation('relu'))
model.add(Dropout(0.5))
model.add(Dense(3))
model.add(Activation('softmax'))

model.compile(loss='categorical_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])

# this is the augmentation configuration we will use for training
train_datagen = ImageDataGenerator(
    rescale=1. / 255,
    shear_range=0.2,
    zoom_range=0.2,
    horizontal_flip=True)

# this is the augmentation configuration we will use for testing:
# only rescaling
test_datagen = ImageDataGenerator(rescale=1. / 255)
predict_datagen = ImageDataGenerator()

train_generator = train_datagen.flow_from_directory(
    train_data_dir,
    target_size=(img_width, img_height),
    batch_size=batch_size)

validation_generator = test_datagen.flow_from_directory(
    validation_data_dir,
    target_size=(img_width, img_height),
    batch_size=batch_size)
print("*********************vaidation_file_names*********************")
print(validation_generator.filenames)

prediction_generator = predict_datagen.flow_from_directory(
    test_data_dir,
    target_size=(img_width, img_height),
    batch_size=batch_size,
    shuffle=False)
model.fit_generator(
    train_generator,
    steps_per_epoch=nb_train_samples // batch_size,
    epochs=epochs,
    validation_data=validation_generator,
    validation_steps=nb_validation_samples // batch_size)
model.save_weights('custom_cnn.h5')


print("*********************prediction_file_names*********************")
print(prediction_generator.filenames)
print("*********************prediction_class_indices*********************")
print(prediction_generator.class_indices)
print("*********************prediction_classes*********************")
print(prediction_generator.classes)
prediction = model.predict_generator(prediction_generator, steps=nb_validation_samples // batch_size, verbose=1)
print("*********************prediction*********************")
print(prediction)
prediction[prediction >= 0.5] = 1
prediction[prediction < 0.5] = 0
print("*********************prediction after threshold*********************")
print(prediction)

correct_counts = 0

for index, i in enumerate(prediction):
    class_index = index//10
    if np.argmax(i)==class_index:
        correct_counts+=1
        print("class: "+str(class_index)+" index: "+str(index)+": is corrected")
    else:
        print("class: "+str(class_index)+" index: "+str(index)+": is wrong")
print("correct counts: "+str(correct_counts)+"  total: "+str(nb_test_samples))
print("final test accuracy: "+str(correct_counts/nb_test_samples))
