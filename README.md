## Censorship-Data-Driven-DNS-Resolution-Anomaly-Detection
This project utilizes bidirectional active probing to gather domain censorship data from various national cyberspaces, encompassing typical domain resolution anomalies, forming a set of DNS resolution anomaly samples.
Additionally, employing stacked ensemble learning, a DNS resolution anomaly detection model is developed.


### 1. Active Detection of National Domain Name Censorship Data
The project offers two detection tools for actively probing national domain name censorship data:

* a. If there is a vantage point within the country, censorship data can be obtained via active DNS resolution within the country's network. 
The corresponding tool code is: *__get_censor_domain_resolve.py__*; 


* b.  In the absence of a vantage point in the concerned country, 
measurement points provided by the [RIPE measuring platform](https://atlas.ripe.net/) can be utilized to achieve this.
The corresponding tool code is: *__ripe_measurement_aip.py__*;

### 2. Active Detection of National Domain Name Censorship Data


##有问题反馈
在使用中有任何问题，欢迎反馈给我，可以用以下联系方式跟我交流

* 邮件(dev.hubo#gmail.com, 把#换成@)
* 微信:jserme
* weibo: [@草依山](http://weibo.com/ihubo)
* twitter: [@ihubo](http://twitter.com/ihubo)
