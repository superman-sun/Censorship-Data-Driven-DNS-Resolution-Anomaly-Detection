## Censorship-Data-Driven-DNS-Resolution-Anomaly-Detection
This project utilizes bidirectional active probing to gather domain censorship data from various national cyberspaces, encompassing typical domain resolution anomalies, forming a set of DNS resolution anomaly samples. Additionally, employing stacked ensemble approach, a DNS resolution anomaly detection model is developed.


### 1. Active Detection of National Domain Name Censorship Data
The project offers two detection tools for actively probing national domain name censorship data:

* a. If there is a vantage point within the country, censorship data can be obtained via active DNS resolution within the country's network. 
The corresponding tool code is: *__get_censor_domain_resolve.py__*; 


* b.  In the absence of a vantage point in the concerned country, 
measurement points provided by the [RIPE measuring platform](https://atlas.ripe.net/) can be utilized to achieve this.
The corresponding tool code is: *__ripe_measurement_aip.py__*;

### 2. Ensemble Algorithm Model and Feature Data

* a. In our ensemble learning algorithm model, the first layer of base models includes: KNN, Logistic Regression (LR),
Support Vector Machine (SVM), Random Forest (RF), AdaBoost Classifier, and ExtraTrees Classifier. In the second-level model, we selected the Boosted Tree Learning Model, XGBoost, as our meta-classifier. Specific code implementation: 


### Issue Feedback
If you encounter any problems, please feel free to reach out to us through the following channels: <br>
Email: 981300198#qq.com (Replace # with @)
