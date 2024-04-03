# encoding:utf-8
"""
日期：2023年09月12日
作者：李超
"""
import json
import math
import os, re
import pandas as pd
from collections import defaultdict
import requests
from collections import Counter
import matplotlib.colors as mcolors
import matplotlib as mpl
from matplotlib.colors import ListedColormap

from data_analysis.ssl_valid import verify_ssl_certificate
from sklearn.preprocessing import  MinMaxScaler #归一化
from sklearn.preprocessing import StandardScaler #标准化
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.tree import DecisionTreeClassifier, export_graphviz
import pydotplus
from sklearn.ensemble import  RandomForestClassifier, ExtraTreesClassifier
from sklearn.metrics import classification_report
from sklearn.metrics import roc_auc_score, roc_curve
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score #轮廓系数
from sklearn.metrics import confusion_matrix
# from lightgbm import LGBMClassifier

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.ensemble import VotingClassifier

from sklearn.ensemble import AdaBoostClassifier
from sklearn.ensemble import GradientBoostingClassifier

import xgboost as xgb
from sklearn.ensemble import BaggingClassifier, StackingClassifier, GradientBoostingClassifier

import torch
import torch.nn.functional as F
import seaborn as sns
import matplotlib.pyplot as plt


# from keras.models import Sequential
# from keras.layers import SimpleRNN, Dense

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import SimpleRNN, Dense

from shared_packages.Logger import Logger
from shared_packages.read_config import SystemConfigParse
from shared_packages.db_manage import MySQL
conf_path = 'shared_packages/system.conf'
logger = Logger(show_terminal=SystemConfigParse(conf_path).read_log_show())

def ensemble_learning(all_train_test_data):
    """
     'x_content_only'
     'x_contend_add_dns'
     'x_contend_add_path'
     'x_contend_add_time'
     'x_all'
    """
    # all_train_test_data.pop('x_all')
    all_train_test_data.pop('x_contend_add_time')
    all_train_test_data.pop('x_contend_add_path')
    all_train_test_data.pop('x_contend_add_dns')
    all_train_test_data.pop('x_content_only')

    knn_clf = KNeighborsClassifier() #1 K近邻
    lg_clf = LogisticRegression()  #2 逻辑回归
    # dt_clf = DecisionTreeClassifier() #决策树，为防止过拟合，可以添加参数：max_depth=4
    svm_clf = SVC(probability=True) #3支持向量机
    rf_clf = RandomForestClassifier()  #4 随机森林
    extra_tree_clf = ExtraTreesClassifier() #5 Extra Trees分类器

    # 三种都属于Boosting（提升法）的集成学习算法
    adaboost_clf = AdaBoostClassifier() #6 adaboost 分类器
    # gradientboost_clf = GradientBoostingClassifier()
    xgb_clf = xgb.XGBClassifier(learning_rate=0.5, n_estimators=8, max_depth=2, use_label_encoder=False,eval_metric=['logloss', 'error'])
    xgb_clf = xgb.XGBClassifier(use_label_encoder=False, eval_metric=['logloss', 'auc', 'error']) #7 XGB分类器

    # 投票分类器，使用软投票soft, 硬投票（hard）,属于stacking
    estimators = [('knn', knn_clf), ('lg', lg_clf), ('svm', svm_clf), ('rf', rf_clf), ('extree', extra_tree_clf), ('adaboost', adaboost_clf)]
    # voting_clf = VotingClassifier(estimators=estimators, voting='hard')

    stacking_clf = StackingClassifier(estimators=estimators, final_estimator = xgb_clf,
                                      stack_method='predict_proba', passthrough=True)

    # Bagging（装袋法）的集成学习算法
    # base_model = svm_clf
    # weight_clf = BaggingClassifier(base_estimator=base_model, n_estimators=6,
    #                                random_state=12)  # 可以调整n_estimators参数来增加集成模型的复杂度


    for k,v in all_train_test_data.items():
        print('%s 数据集训练结果：' % k)
        x_train, x_test, y_train, y_test = v


        #打印三个基础算法+集成投票算法的准确率
        save_fpr_tpr = dict()
        styles = [
            {"color": "blue", "linestyle": "-", "clf_name":'KNN'},
            {"color": "green", "linestyle": "--", "clf_name":'LR'},
            {"color": "red", "linestyle": "-.", "clf_name":'SVM'},
            {"color": "cyan", "linestyle": ":", "clf_name":'RF'},
            {"color": "magenta", "linestyle": "-", "clf_name":'Adaboost'},
            {"color": "yellow", "linestyle": "--", "clf_name":'ExtraTrees'},
            {"color": "black", "linestyle": "-.", "clf_name":'Stacking'}
        ]
        predict_all = []
        plt.figure(figsize=(8, 6))
        # for clf in (stacking_clf, ):
        for indx, clf in enumerate((knn_clf, lg_clf, svm_clf, rf_clf, extra_tree_clf, adaboost_clf, stacking_clf)):
            clf.fit(x_train, y_train)
            y_predict = clf.predict(x_test)
            predict_all.append(y_predict.tolist())
            acc = accuracy_score(y_test, y_predict) * 100 #准确率
            precision = precision_score(y_test, y_predict) * 100 #精确率
            recall = recall_score(y_test, y_predict) * 100  #召回率
            f1 = f1_score(y_test, y_predict) * 100 #F1分数
            auc = roc_auc_score(y_test, y_predict)
            print(clf.__class__.__name__,'的准确率为:%.4f%%，精确率:%.4f%%，召回率:%.4f%%，'
                                         'F1分数:%.4f%%, auc系数:%s' % (acc, precision, recall, f1, auc))

            #输出ROC曲线
            # 计算 ROC 曲线的假正例率（FPR）和真正例率（TPR）
            y_proba = clf.predict_proba(x_test)[:, 1]
            fpr, tpr, thresholds = roc_curve(y_test, y_proba)  # 使用模型的概率预测值
            plt.plot(fpr, tpr, color=styles[indx]['color'], lw=2, label='%s AUC = %0.2f' %
                                                               (styles[indx]['clf_name'], auc), linestyle=styles[indx]['linestyle'])
            save_fpr_tpr[styles[indx]['clf_name']] = {
                'fpr': fpr.tolist(),
                'tpr': tpr.tolist(),
                'auc': auc
            }

        predictions_df = pd.DataFrame({'KNN': predict_all[0], 'LR': predict_all[1], 'SVM': predict_all[2],
                                       'RF': predict_all[3], 'ExtraTrees': predict_all[4], 'Adaboost': predict_all[5]})


        #绘制6个基础模型预测结果的相关系数热力图
        correlation_matrix = predictions_df.corr()
        # with open('figure/base_6_model_correlation.json', 'w', encoding='utf-8') as fp:
        #     fp.write(correlation_matrix.to_json())

        plt.figure(figsize=(10, 8))
        ax = sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', linewidths=0.5, fmt=".2f",
                    annot_kws={"size": 12},
                    cbar_kws={"shrink":0.95, "format": "%.2f"})

        # 设置色带标签的字体大小
        cbar = ax.collections[0].colorbar
        cbar.ax.tick_params(labelsize=12)  # 你可以根据需要更改大小

        plt.yticks(fontsize=12)
        plt.xticks(fontsize=12)
        plt.savefig('./figure/predict_heatmap.pdf', bbox_inches='tight')
        plt.show()

        #绘制7个模型的ROC曲线图
        plt.plot([0, 1], [0, 1], color='navy', lw=2, label='Baseline AUC = 0.50', linestyle='--')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve')
        plt.legend(loc="lower right")
        plt.show()

        # with open('figure/roc.json', 'w', encoding='utf-8') as fp:
        #     fp.write(json.dumps(save_fpr_tpr))

        # MDL(v)
        print('*' * 50)

    # get_average_importance(all_train_test_data, stacking_clf)

def get_train_test_data(smaple_number):
    df_feature = pd.read_csv('features.csv')

    x = df_feature.iloc[:, :-1]  # 特征值

    columns = x.columns.tolist()
    y = df_feature['label']  # 目标值
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

    #DNS属性
    dns_features = ['edns_-1', 'edns_0']

    #解析路径特征
    path_features = ['rep_ping_time_f']
    #时间特征
    time_features = ['ip_ratio']

    #(1)只有响应内容特征
    # x_content_only = x.drop(dns_features + path_features + time_features, axis=1, inplace=False)
    x_content_only_train = x_train.drop(dns_features + path_features + time_features, axis=1, inplace=False)
    x_content_only_test = x_test.drop(dns_features + path_features + time_features, axis=1, inplace=False)
    #(2)在响应内容基础上，添加DNS属性
    # x_contend_add_dns = x.drop(path_features + time_features, axis=1, inplace=False)
    x_contend_add_dns_train = x_train.drop(path_features + time_features, axis=1, inplace=False)
    x_contend_add_dns_test = x_test.drop(path_features + time_features, axis=1, inplace=False)
    #(3)在响应内容基础上，添加解析路径特征
    # x_contend_add_path = x.drop(dns_features + time_features, axis=1, inplace=False)
    x_contend_add_path_train = x_train.drop(dns_features + time_features, axis=1, inplace=False)
    x_contend_add_path_test = x_test.drop(dns_features + time_features, axis=1, inplace=False)
    #(4)在响应内容基础上，添加时间特征
    # x_contend_add_time = x.drop(dns_features + path_features, axis=1, inplace=False)
    x_contend_add_time_train = x_train.drop(dns_features + path_features, axis=1, inplace=False)
    x_contend_add_time_test = x_test.drop(dns_features + path_features, axis=1, inplace=False)
    #(5)响应内容、DNS属性、路径、时间四个维度特征都有
    x_all_train = x_train
    x_all_test = x_test

    all_type_data = {
        'x_content_only': (x_content_only_train, x_content_only_test),
        'x_contend_add_dns': (x_contend_add_dns_train, x_contend_add_dns_test),
        'x_contend_add_path': (x_contend_add_path_train, x_contend_add_path_test),
        'x_contend_add_time': (x_contend_add_time_train, x_contend_add_time_test),
        'x_all': (x_all_train, x_all_test)
    }

    # 数据集划分
    all_train_test_data = {}
    for k, v in all_type_data.items():
        # x_train, x_test, y_train, y_test = train_test_split(v, y, test_size=0.3, random_state=12)
        x_train, x_test = v
        # 特征标准化
        scaler = StandardScaler()
        x_train = scaler.fit_transform(x_train)
        x_test = scaler.transform(x_test)

        all_train_test_data[k] = (x_train, x_test, y_train, y_test)

    return all_train_test_data, columns

def anomaly_detction_by_ml():

    all_train_test_data, columns = get_train_test_data(0.5)

    #使用集成算法实现，基础算法有逻辑回归、随机森林、支持向量机
    ensemble_learning(all_train_test_data)

def main():

    #利用机器学习算法，实现DNS解析数据异常判断
    anomaly_detction_by_ml()

if __name__ == '__main__':
    main()