import os
from scipy import stats
from sklearn.model_selection import RandomizedSearchCV
from xgboost import XGBClassifier, XGBRegressor
import lightgbm as lgb
from catboost import CatBoostClassifier, CatBoostRegressor

TRAINING = os.environ.get("TRAINING_DATA")
VALIDATION = os.environ.get("VALIDATION_DATA")
MODEL = os.environ.get("MODEL")
PROBLEM_TYPE = os.environ.get("PROBLEM_TYPE")

class TuneParams:
    def __init__(self, training_data, model, problem_type):
        self.training_data = training_data
        self.model = model
        self.problem_type = problem_type

    def _xgboost(self):
        
        param_dist = {'n_estimators': stats.randint(150, 500),
              'learning_rate': stats.uniform(0.01, 0.07),
              'subsample': stats.uniform(0.3, 0.7),
              'max_depth': [3, 4, 5, 6, 7, 8, 9],
              'colsample_bytree': stats.uniform(0.5, 0.45),
              'min_child_weight': [1, 2, 3]
             }

        if self.problem_type == 'regression':
            model_xgb = XGBRegressor()
            model = RandomizedSearchCV(model_xgb,
                                 param_distributions = param_dist, 
                                 n_iter = 25, 
                                 scoring = 'r2', 
                                 error_score = 0, verbose = 3, n_jobs = -1)

        elif self.problem_type == 'classification':
            model_xgb = XGBClassifier()
            model = RandomizedSearchCV(model_xgb,
                                 param_distributions = param_dist, 
                                 n_iter = 25, 
                                 scoring = 'f1', 
                                 error_score = 0, verbose = 3, n_jobs = -1)
        
        elif self.problem_type == 'multiclass':
            model_xgb = XGBClassifier()
            model = RandomizedSearchCV(model_xgb,
                                 param_distributions = param_dist, 
                                 n_iter = 25, 
                                 scoring = 'f1_weighted', 
                                 error_score = 0, verbose = 3, n_jobs = -1)


        else:
            raise Exception("Problem Type not supported")

        model.fit(self.training_data.drop(['TARGET'], axis = 1), self.training_data['TARGET'])

        return model.best_params_

    def _lightgbm(self):
        
        if self.problem_type == 'regression':
            estimator = lgb.LGBMRegressor(num_leaves = 30)

        elif self.problem_type == 'classification':
            estimator = lgb.LGBMClassifier(objective = 'binary', num_leaves = 30)

        elif self.problem_type == 'multiclass':
            estimator = lgb.LGBMClassifier(objective = 'multiclass', num_leaves = 30)

        param_grid = {
                'learning_rate': stats.uniform(0.01, 0.2),
                'n_estimators': [400, 500, 520, 540, 560, 580, 600, 700, 800, 1000]
        }

        model = RandomizedSearchCV(estimator, param_grid, cv=3)
        model.fit(self.training_data.drop(['TARGET'], axis = 1), self.training_data['TARGET'])

        return model.best_params_

    def _catboost(self):
        
        if self.problem_type == 'regression':
            model = CatBoostRegressor()
        elif self.problem_type == 'classification':
            model = CatBoostClassifier()
        elif self.problem_type == 'multiclass':
            model = CatBoostClassifier(loss_function='MultiClass')
        else:
            raise Exception('Problem Type Not supported!')

        #model.fit(self.training_data.drop(['TARGET'], axis = 1), self.training_data['TARGET'])

        grid = {'learning_rate': stats.uniform(0.01, 0.2),
                'depth': [4, 6, 10],
                'l2_leaf_reg': [1, 3, 5, 7, 9]}

        randomized_search_result = model.randomized_search(grid,
                                                   X=self.training_data.drop(['TARGET'], axis = 1),
                                                   y=self.training_data['TARGET'])
        
        return randomized_search_result['params']

    def get_params(self):

        if self.model == "xgboost":
            return self._xgboost()

        elif self.model == "lightgbm":
            return self._lightgbm()

        elif self.model == "catboost":
            return self._catboost()

        else:
            raise Exception("Model not supported")

if __name__ == "__main__":
    df_train = pd.read_csv(TRAINING)
    df_valid = pd.read_csv(VALIDATION)
    df = pd.concat([df_train, df_valid], axis = 0)
    Tuner = TuneParams(df, model = MODEL, problem_type = PROBLEM_TYPE)

    params = Tuner.get_params()
    

