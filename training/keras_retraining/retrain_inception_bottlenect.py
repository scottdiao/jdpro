import numpy as np
from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential
from keras.layers import Dropout, Flatten, Dense, Activation
from keras.utils.np_utils import to_categorical
from keras import applications, optimizers
import os, os.path

# dimensions of our images.
img_width, img_height = 299, 299

top_model_weights_path = 'bottleneck_fc_model.h5'
train_data_dir = 'building_photos/train_20'
validation_data_dir = 'building_photos/train_20'
test_data_dir = 'building_photos/train_20'
class_counts = len(os.listdir(train_data_dir))
nb_train_samples = sum([len(files) for r, d, files in os.walk(train_data_dir)])
nb_validation_samples = sum([len(files) for r, d, files in os.walk(validation_data_dir)])
nb_test_samples = sum([len(files) for r, d, files in os.walk(test_data_dir)])
print("nb_train_samples: "+str(nb_train_samples))
print("nb_validation_samples: "+str(nb_validation_samples))
print("nb_test_samples: "+str(nb_test_samples))

epochs = 3
batch_size = 40

def save_bottlebeck_features():
    datagen = ImageDataGenerator(rescale=1. / 255)

    # build the VGG16 network
    model = applications.InceptionV3(include_top=False, weights='imagenet')

    generator = datagen.flow_from_directory(
        train_data_dir,
        target_size=(img_width, img_height),
        batch_size=1,
        class_mode=None,
        shuffle=False)
    bottleneck_features_train = model.predict_generator(
        generator, nb_train_samples)
    print("*************class_indices***************")
    print(str(generator.class_indices).encode('utf-8'))

    train_filenames = np.asarray(generator.filenames)
    np.save('./bottleneck/inception_v3_bottleneck_features_train.npy',
            bottleneck_features_train)

    generator = datagen.flow_from_directory(
        validation_data_dir,
        target_size=(img_width, img_height),
        batch_size=1,
        class_mode=None,
        shuffle=False)
    validation_filenames = np.asarray(generator.filenames)
    bottleneck_features_validation = model.predict_generator(
        generator, nb_validation_samples)
    np.save('./bottleneck/inception_v3_bottleneck_features_validation.npy',
            bottleneck_features_validation)

    generator = datagen.flow_from_directory(
        test_data_dir,
        target_size=(img_width, img_height),
        batch_size=1,
        class_mode=None,
        shuffle=False)
    bottleneck_features_test = model.predict_generator(
        generator, nb_test_samples)
    np.save('./bottleneck/inception_v3_bottleneck_features_test.npy',
            bottleneck_features_test)
    return train_filenames, validation_filenames


def train_top_model():
    train_data = np.load('./bottleneck/inception_v3_bottleneck_features_train.npy')
    c = 0
    for r, d, files in sorted(os.walk(train_data_dir)):
        if(len(files)!=0):
            print(str(c)+"str: "+"  "+str(r)+"  "+str(len(files)))
            if c==0:
                train_labels = np.array([0]*len(files))
            else:
                train_labels = np.concatenate((train_labels, np.array([c]*len(files))))
            c+=1
    train_labels = to_categorical(train_labels)


    validation_data = np.load('./bottleneck/inception_v3_bottleneck_features_validation.npy')
    c=0
    for r, d, files in sorted(os.walk(validation_data_dir)):
        if(len(files)!=0):
            if c==0:
                validation_labels = np.array([0]*len(files))
            else:
                validation_labels = np.concatenate((validation_labels, np.array([c]*len(files))))
            c+=1

    validation_labels = to_categorical(validation_labels)

    test_data = np.load('./bottleneck/inception_v3_bottleneck_features_test.npy')
    c=0
    for r, d, files in sorted(os.walk(test_data_dir)):
        if(len(files)!=0):
            if c==0:
                test_labels = np.array([0]*len(files))
            else:
                test_labels = np.concatenate((test_labels, np.array([c]*len(files))))
            c+=1
    test_labels = to_categorical(test_labels)

    model = Sequential()
    model.add(Flatten(input_shape=train_data.shape[1:]))
    model.add(Dense(256))
    model.add(Activation('relu'))
    model.add(Dense(class_counts))
    model.add(Activation('softmax'))

    rms = optimizers.RMSprop()
    model.compile(optimizer='sgd',
                  loss='categorical_crossentropy', metrics=['accuracy'])

    model.fit(train_data, train_labels,
              epochs=epochs,
              validation_data=(validation_data, validation_labels))
    model.save_weights(top_model_weights_path)

    score = model.evaluate(train_data, train_labels, verbose=0)
    print('Train loss:', score[0])
    print('Train accuracy:', score[1])
    score = model.evaluate(validation_data, validation_labels, verbose=0)
    print('validation loss:', score[0])
    print('validation accuracy:', score[1])
    score = model.evaluate(test_data, test_labels, verbose=0)
    print('test_data loss:', score[0])
    print('test_data accuracy:', score[1])

    correct_counts=0
    prediction = model.predict(test_data, verbose=1)
    train_prediction = model.predict(train_data, verbose=1)
    validation_prediction = model.predict(validation_data, verbose=1)
    print("*********************train prediction*********************")
    # print(train_filenames)
    f= open("train_result.txt","w+")
    for index, i in enumerate(train_prediction):
        if index >= len(train_filenames) or index >= len(train_labels):
            break
        f.write(" index: "+str(index)+"  "+str(str(train_filenames[index]).encode('utf-8'))+"perdiction: "+str(np.argmax(i))+" label: "+str(np.argmax(train_labels[index]))+"\r\n")
        if np.argmax(i) == np.argmax(train_labels[index]):
            correct_counts+=1
    f.close()
    print("correct train counts: "+str(correct_counts)+"  total: "+str(nb_train_samples))
    print("final train accuracy: "+str(correct_counts/nb_train_samples))

    correct_counts=0
    print("*********************validation prediction*********************")
    # print(validation_filenames)
    for index, i in enumerate(validation_prediction):
        if index >= len(validation_filenames) or index >= len(validation_labels):
            break
        if np.argmax(i) == np.argmax(validation_labels[index]):
            correct_counts+=1
            # print("is corrected")
        else:
            if index >= len(validation_filenames):
                break
            # print(" index: "+str(index)+"  "+str(str(validation_filenames[index]).encode('utf-8'))+"perdiction: "+str(np.argmax(i))+" label: "+str(np.argmax(validation_labels[index])))
            print("is wrong")

    print("correct validation counts: "+str(correct_counts)+"  total: "+str(nb_validation_samples))
    print("final validation accuracy: "+str(correct_counts/nb_validation_samples))

    correct_counts=0
    print("*********************test prediction*********************")
    for index, i in enumerate(prediction):
        class_index = index//10
        if np.argmax(i)==class_index:
            correct_counts+=1
            # print("class: "+str(class_index)+" index: "+str(index)+": is corrected")
        # else:
            # print("class: "+str(class_index)+" index: "+str(index)+": is wrong")
    print("correct counts: "+str(correct_counts)+"  total: "+str(nb_test_samples))
    print("final test accuracy: "+str(correct_counts/nb_test_samples))

# train_filenames, validation_filenames = save_bottlebeck_features()
# train_top_model(train_filenames, validation_filenames)
train_top_model()
