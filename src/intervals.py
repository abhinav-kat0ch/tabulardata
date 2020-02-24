from nonconformist.cp import IcpClassifier, IcpRegressor
from nonconformist.nc import NcFactory
from sklearn.neighbors import KNeighborsRegressor
from catboost import CatBoostRegressor
import pandas as pd
import numpy as np
import joblib
import os
from .hyperparamtuner import TuneParams

TRAINING = os.environ.get("TRAINING_DATA")
VALIDATION = os.environ.get("VALIDATION_DATA")
CALIBRATION = os.environ.get("CALIBRATION_SET")
TEST = os.environ.get("TEST_DATA")
PROBLEM_TYPE = os.environ.get("PROBLEM_TYPE")
MODEL = os.environ.get("MODEL")
DATASET = os.environ.get("DATASET")

df_train = pd.read_csv(TRAINING)
df_valid = pd.read_csv(VALIDATION)
df_cal = pd.read_csv(CALIBRATION)
df_test = pd.read_csv(TEST)
trainX, trainY = df_train.drop(['TARGET'],  axis = 1), df_train['TARGET']
calX, calY = df_cal.drop(['TARGET'], axis = 1), df_cal['TARGET']

model = joblib.load(os.path.join("models", f"{MODEL}.pkl"))
if 'TARGET' in df_test.columns:
    testX, testY = df_test.drop(['id', 'TARGET'], axis = 1), df_test['TARGET']
else:
    testX = df_test.drop(['id'], axis = 1)

if PROBLEM_TYPE == 'classification':
    if MODEL == 'catboost':
        raise Exception('Cant compute inervals for CatBoostClassifier!')
        
    nc = NcFactory.create_nc(model, normalizer_model=KNeighborsRegressor(n_neighbors=11))	# Create a default nonconformity function
    icp = IcpClassifier(nc)

    icp.fit(trainX.values, trainY.values)

    # Calibrate the ICP using the calibration set
    icp.calibrate(calX.values, calY.values)

    # Produce predictions for the test set, with confidence 95%
    prediction = icp.predict(testX.to_numpy(), significance=0.05)


else:
    if MODEL == 'catboost':
        params = joblib.load("models/params.pkl")
        
        model = CatBoostRegressor()
        model.set_params(**params, loss_function='Quantile:alpha=0.025')
        model.fit(trainX, trainY)
        lower = model.predict(testX.to_numpy())

        model = CatBoostRegressor()
        model.set_params(**params, loss_function='Quantile:alpha=0.975')
        model.fit(trainX, trainY)
        upper = model.predict(testX.to_numpy())

        prediction = list(zip(lower,  upper))
    else:
        nc = NcFactory.create_nc(model, normalizer_model=KNeighborsRegressor(n_neighbors=11))	# Create a default nonconformity function
        icp = IcpRegressor(nc)			# Create an inductive conformal regressor

        # Fit the ICP using the proper training set
        icp.fit(trainX.values, trainY.values)

        # Calibrate the ICP using the calibration set
        icp.calibrate(calX.values, calY.values)

        # Produce predictions for the test set, with confidence 95%
        prediction = icp.predict(testX.to_numpy(), significance=0.05)

sub = pd.DataFrame(prediction, columns = ['lower_bound', 'upper_bound'])
sub.to_csv(f"models/{PROBLEM_TYPE}_{MODEL}_{DATASET}_intervals.csv", index = False)