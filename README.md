## Censorship-Data-Driven-DNS-Resolution-Anomaly-Detection
This project utilizes bidirectional active probing to gather domain censorship data from various national cyberspaces, encompassing typical domain resolution anomalies, forming a set of DNS resolution anomaly samples. Additionally, employing stacked ensemble approach, a DNS resolution anomaly detection model is developed.


### 1. Active Detection of National Domain Name Censorship Data
The project offers two detection tools for actively probing national domain name censorship data:

* a. If there is a vantage point within the country, censorship data can be obtained via active DNS resolution within the country's network. 
The corresponding tool code is: *__get_censor_domain_resolve.py__*; 


* b.  In the absence of a vantage point in the concerned country, 
measurement points provided by the [RIPE measuring platform](https://atlas.ripe.net/) can be utilized to achieve this.
The corresponding tool code is: *__ripe_measurement_aip.py__*;

### 2. Ensemble Algorithm Model and Source Data

* a. In our ensemble learning algorithm model, the first layer of base models includes: KNN, Logistic Regression (LR),
Support Vector Machine (SVM), Random Forest (RF), AdaBoost Classifier, and ExtraTrees Classifier. In the second-level model, we selected the Boosted Tree Learning Model, XGBoost, as our meta-classifier. Specific code implementation: *__ml_extract_features.py__*.

* b. The source data we provide includes some domain name resolution raw data (8__2023_08_24_china_censor_resolution.zip__*) and some refined feature data (*__features.csv__*).
If you need more data, you can contact us via email.

### 3. Software Configuration
For the project to carry out proactive domain name detection and resolution, it is necessary to use different measurement points in multiple network spaces. 
Therefore, to improve detection efficiency, *__RabbitMQ__* queues have been utilized to implement distributed detection. Consequently, it is necessary to set up 
RabbitMQ and the storage database MySql.



### Issue Feedback
If you encounter any problems, please feel free to reach out to us through the following channels: <br>
Email: 981300198#qq.com (Replace # with @)
