# -*- coding: utf-8 -*-
"""영화관객예측(데이콘)_RF.ipynb

# 1. 데이터 불러오기
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib
import seaborn as sns
import warnings
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error
import math
from sklearn.ensemble import RandomForestRegressor

train = pd.read_csv("C:/Users/seunghyeon/Desktop/dacon/movie/movies_train.csv")
test = pd.read_csv("C:/Users/seunghyeon/Desktop/dacon/movie/movies_test.csv")

# train, test 데이터 합침
movie = pd.concat([train, test], axis=0)
print("train shape: ", train.shape)
print("test shape: ", test.shape)
print("movie shape: ", movie.shape)
movie.reset_index(inplace=True, drop=True)

# train, test data 구분하는 column "is_test" 추가
movie['is_test'] = movie['box_off_num'].isnull()
movie.tail()

"""- NULL 값 확인"""

#null값은 0으로 처리 
movie['dir_prev_bfnum'].fillna(value=movie['dir_prev_bfnum'].min(),inplace=True)
movie.isnull().sum()

"""# EDA"""

# 명목형 변수 uniq 값 확인
for col in ['distributor','genre','release_time','screening_rat','director']:
  uniq = np.unique(movie[col].astype('str'))
  print('-'*70)
  print('# col {}, uniq {}, uniq {}'.format(col, len(uniq), uniq))

#명목형 변수의 uniqe 값과 빈도수 알아보기
def uniqes(s):
  uniqs, freqs = np.unique(s, return_counts=True)
  t = sorted(zip(uniqs, freqs), reverse=True, key=lambda x: x[1])
  t = pd.DataFrame(t)
  return t

# uniqes(movie['distributor'])[:9].sum()
# uniqes(movie['genre'])
# uniqes(movie['release_time'])
# uniqes(movie['screening_rat'])
# uniqes(movie['director'])[:5].sum()

"""- 명목형 변수 중 일부(distributor, director)는 빈도 기준으로 다시 레이블링"""

def label_by_freq(s, count, dtype=np.int64) :
  uniqs, freqs = np.unique(s, return_counts=True)

  top = sorted(zip(uniqs, freqs), key=lambda x: x[1], reverse=True)[:count]
  top_map = {a[0]:(b+1) for a,b in zip(top, range(len(top)))}

  return s.map(lambda x: top_map.get(x,0)).astype(dtype)

movie['distributor'] = label_by_freq(movie['distributor'], 9)
movie['director'] = label_by_freq(movie['director'], 5)


# -한글지원 문제
fontpath = 'C:/Windows/Fonts/H2GTRE.ttf'
font_name = fm.FontProperties(fname=fontpath).get_name()
matplotlib.rc('font', family=font_name)


# 명목형 변수의 분포 확인
# - 그리기

COLOR = 'black'

cols = ['distributor','genre','screening_rat','director']
def draw_barplot(column,df):
    # f,ax = plt.subplots(figsize=(15,10))
    sns.barplot(x=column, y='box_off_num',data=df)
    #sns.countplot(x=col, data=df, alpha=0.5)
    plt.rcParams['text.color'] = COLOR
    plt.rcParams['axes.labelcolor'] = COLOR
    plt.rcParams['xtick.color'] = COLOR
    plt.rcParams['ytick.color'] = COLOR
    plt.legend()
    plt.show()

def draw_barplot_group(column, df, hue=None):
  f, ax = plt.subplots(figsize=(10,5))
  sns.countplot(x=column, hue=hue, data=df, alpha=0.5)
  plt.xlabel(column)
  plt.show()

for col in cols:
  print('-' * 50)
  print('col name: ',col)
  draw_barplot(col, movie)

for col in cols:
  draw_barplot_group(col, movie, 'is_test')

# 연속형 변수간 상관성 확인
sns.pairplot(movie[['time','dir_prev_bfnum','dir_prev_num','num_staff','num_actor','box_off_num']], kind='reg')
plt.show()

cor = movie[['time','dir_prev_bfnum','dir_prev_num','num_staff','num_actor','box_off_num']].corr()
sns.heatmap(data = cor, annot=True, cmap='Blues',xticklabels=True, yticklabels=True)
plt.show()

# 명목형 변수중 release_time 로 year, month , 계절 변수 생성
def date_split(str_date):
  if str_date.__class__ is float and math.isnan(str_date) or str_date == "":
    return np.nan
  Y, M, D = [int(a) for a in str_date.strip().split("-")]

  if M in [12,1,2]:
    S = 'winter'
  elif M in [3,4,5]:
    S = 'spring'
  elif M in [6,7,8]:
    S = 'summer'
  elif M in [9,10,11]:
    S = 'autumm'
  else:
    S = np.nan

  return Y, M, S

new = pd.DataFrame(movie['release_time'].map(date_split).tolist())
movie['year'] = new[0]
movie['month'] = new[1]
movie['season'] = new[2]

del new
del movie['release_time']

# 새로 만든 season 변수/year 변수와 box_off_num 변수 간 상관성 확인 -> season 별 box_off_num 평균에 차이가 있어보임

sns.countplot(x='season', data=movie, alpha=0.5)
plt.show()

sns.barplot(x='year', y='box_off_num',data=movie,alpha=0.5)
plt.show()

sns.pairplot(movie[['time','dir_prev_bfnum','dir_prev_num','num_staff','num_actor','box_off_num']], kind='reg')
plt.show()

plt.boxplot(train['box_off_num'])
plt.show()

sns.boxplot(x='season',y='box_off_num',data=movie[movie['is_test']==False])
plt.xlabel("Season", fontsize=25)
plt.ylabel("boxoffice number(관객 수)", fontsize=25)
plt.xticks(fontsize=20)
plt.show()

sns.boxplot(x='month',y='box_off_num',data=movie)
plt.xlabel("Month", fontsize=25)
plt.ylabel("boxoffice number(관객 수)", fontsize=25)
plt.xticks(fontsize=20)
plt.show()

"""- 명목형 변수를 one hot encoding 함"""

# label encoding 수행
to_label_col = ['genre','screening_rat','season'] #문자형을 숫자로 encoding
to_onehot_label_col = ['screening_rat','year','season','distributor','director'] #숫자형을 onehot encoding # 'genre''month' 제외

def one_hot(d, to_label, to_onehot_label):

  temp = d.copy()

  for col in to_label :
    if temp[col][0].__class__ is not float or int :
      encoder = LabelEncoder()
      encoder.fit(temp[col])
      temp[col] = encoder.transform(temp[col])
    else:
      continue

  for col in to_onehot_label :
    encoder = OneHotEncoder(sparse=False)
    X_encoded = encoder.fit_transform(temp[[col]])
    X_encoded = pd.DataFrame(X_encoded)

    X_encoded.columns = encoder.get_feature_names([col])

    temp.drop(col, axis=1, inplace=True)
    temp = pd.concat([temp, X_encoded], axis=1)

  return temp

movie_df = one_hot(movie, to_label_col, to_onehot_label_col)

# 연속형 변수는 표준화 (min, max 이용)
numeric_col = ['time','num_staff','dir_prev_bfnum','dir_prev_num','box_off_num'] # 'num_actor'
# numeric_col = ['box_off_num']
def minmax_stand(data,cols):
  temp = data.copy()

  for col in cols:
    max_ = temp[col].max()
    min_ = temp[col].min()

    temp[col] = ( temp[col]-min_ ) / (max_ - min_)

  return temp

movie_df = minmax_stand(movie_df, numeric_col)
movie_df.head()

"""# -**Baseline**

- 0) train/test data 분할
"""

movie_df.columns

input = movie_df[movie_df['is_test']==False].copy() #원래 train data만 따로 copy
target = movie_df[movie_df['is_test']==False]['box_off_num']

del input['box_off_num'], input['num_actor'],input['title'], input['is_test'], input['genre'], input['month'] # input에서 target값+"title"+"is_test"+필요없다고 생각되는 변수 제외


print('cols: ', input.columns, '\n *** END ***')

X_train, X_val, y_train, y_val = train_test_split(input, target, test_size=0.1, random_state=0)

X_test = movie_df[movie_df['is_test']==True].copy()

del X_test['box_off_num'], X_test['num_actor'], X_test['is_test'], X_test['genre'], X_test['month'] # input에서와 마찬가지로 제외시킴 (단 "title"은 submission 파일에 사용해야함)
print('input shape: ', input.shape, '\n target shape: ', target.shape)

"""- 0-1) 함수 미리 만들기"""

# model을 fitting 시키면서 cross validation으로 평균 scoring값 보여줌
def fit_model(model, x, y, cv_num):
  fit_model = model.fit(x, y)
  scores = cross_val_score(fit_model, x, y, cv=cv_num, scoring='neg_mean_squared_error' )
  score = (scores*(-1)).mean()
  return fit_model, score

# model을 테스트 데이터로 예측했을 때의 예측값보여주는 함수
def predict_model(fit_model, x, y ):
  predicted = fit_model.predict(x)
  mse_ = mean_squared_error(y, predicted)
  return predicted, math.sqrt(mse_)

# 표준화적용하여 값 계산
def cal_origin_score(s):
  maax = movie['box_off_num'].max() 
  miin = movie['box_off_num'].min()
  ad_score = s * (maax - miin) + miin
  return ad_score

"""- 1) RandomForest"""

max_depth_list = []

RF_model = RandomForestRegressor(n_estimators=300,
                              n_jobs=-1,
                              random_state=0, max_depth=13)


RF_model, score = fit_model(RF_model, X_train, y_train, 5)
print(cal_origin_score(score))
print(score)
RF_pred, RF_rmse = predict_model(RF_model, X_val, y_val)
print(RF_rmse)
# 154049.69653460564
# 0.010800759637742446
# 0.10124127230545303

#제출용
RF_model,score = fit_model(RF_model,input,target,5)
print(cal_origin_score(score))
print(score) '''end'''

##validation data로 시각화
val_pred_y = RF_model.predict(X_val)
temp = pd.DataFrame({'pred':val_pred_y,'y_val':y_val})
temp.reset_index(inplace=True)
plt.plot('pred',data=temp)
plt.plot('y_val',data=temp)
plt.legend()
plt.show() 

plt.fill_between(temp.index,'pred',data=temp,COLOR="lightpink",alpha=0.4,label="predicted_value")
plt.fill_between(temp.index,'y_val',data=temp,COLOR='skyblue',alpha=0.4,label="y_validation value")
plt.legend(fontsize=20)
plt.ylabel("standardized boxoffice number",fontsize=20)
plt.xlabel("index",fontsize=20)
plt.show()  '''end'''

max_depth_list = []

RF_model2 = RandomForestRegressor(n_estimators=300,
                              n_jobs=-1,
                              random_state=0, max_depth=11)

RF_model2, score2 = fit_model(RF_model2, X_train, y_train, 5)
print(cal_origin_score(score2))
print(score2)
RF_pred2, RF_rmse2 = predict_model(RF_model2, X_val, y_val)
print(RF_rmse2)
# 154319.70751641344
# 0.010819690818464263
# 0.10316123842443875

maxx = movie['box_off_num'].max()
miin = movie['box_off_num'].min()
math.sqrt(mean_squared_error([(a+b)/2 for a, b in zip(RF_pred, RF_pred2)], y_val)) * (maxx-miin) + miin

submission = pd.DataFrame({'title':X_test['title'],'box_off_num': cal_origin_score(RF_model.predict(X_test.iloc[:,1:]))}) #RF_model: input(즉, 원래 Train data)으로 학습한 모델
submission.head()
submission.to_csv("submission_pred.csv", sep=',',index=False)


