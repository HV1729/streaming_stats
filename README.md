# onlinestats
online_stats_counter
A tornado and redis based web api around http://www.johndcook.com/blog/skewness_kurtosis/


Why to use:
==========================
Now setting up Benchmarking is as easy as 

1. Figure out your cohort and data points and unique names for them
2. setup this backend for the baseline/benchmarking stats
3. Find the places in your frontend/UI and setup js-event-triggers to send REST API requests.


Pros:
===========================
1. Keep track of your data's distribution/summary statistics with very little overhead.(it's (length of) 5 strings on the redis key-value store and (length of the )key you chose)
2. Easy way to provide baseline/benchmarking statistics  for your customers.*
3. CPU overhead is lower by exponential times compared to the conventional method of generating these stats
4. Easy to Setup and Deploy the backend

Cons:
============================
1. Slightly inaccurate, but the error margin declines with number of data points.
2. Takes  up some RAM and CPU(updation involves floating point math).
3. Needs changes throughout the frontend to actually stream the data at right events.

How to use:
==========================

1. To add a new stat: Send a HTTP POST request to
   <hostname>/stats/init?account_name=<name>&stats_name=<name>. (make sure the stat doesn't
   exist already by api below)

2. To check existing stats: Send a HTTP GET request to
   <hostname>/stats?account_name=<name>&stats_name=<name>.

3. To update an existing stat with new value/data point: Send a HTTP POST request to
   <hostname>/stats?account_name=<name>&stats_name=<name>&value=<value>

Currently Hosted:
=============================
Currently hosted on heroku here. (https://online-stats.herokuapp.com/)

* -- Be warned, making sure it's relevant and meaningful still involves rightly grouping/cohorting/segregating the customers. 
