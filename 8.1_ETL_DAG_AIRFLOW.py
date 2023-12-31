# coding=utf-8
from datetime import datetime, timedelta
import pandas as pd
from io import StringIO
import requests
from airflow.decorators import dag
from airflow.decorators import task
from airflow.operators.python import get_current_context


# Функция для CH
def ch_get_df(query='Select 1', host='https://clickhouse.lab.karpov.courses', user='student', password='dpo_python_2020'):
    r = requests.post(host, data=query.encode("utf-8"), auth=(user, password), verify=False)
    result = pd.read_csv(StringIO(r.text), sep='\t')
    return result

# Дефолтные параметры, которые прокидываются в таски
default_args = {
    'owner': 'a.batalov',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2022, 3, 10),
}

# Интервал запуска DAG
schedule_interval = '0 23 * * *'
    
@dag(default_args=default_args, schedule_interval=schedule_interval, catchup=False)
def dag_sim_fin():
    metric_list = ['event_date', 'likes', 'views', 'messages_sent', 'messages_recieved', 'users_sent', 'users_recieved']

    @task()
    def extract_feed():
        query = """SELECT
                       toDate(time) as event_date,
                       gender,
                       age,
                       os,
                       user_id as user,
                       countIf(action = 'like') as likes,
                       countIf(action = 'view') as views
                    FROM
                        simulator.feed_actions 
                    WHERE 
                        toDate(time) = '2022-01-26' 
                    GROUP BY
                        event_date,
                        gender,
                        age,
                        os,
                        user
                    format TSVWithNames"""
        df_cube = ch_get_df(query)
        return df_cube
        
    @task()
    def extract_messages():
        query = """SELECT
                       event_date,
                       gender,
                       age,
                       user,
                       os,
                       messages_sent,
                       messages_recieved,
                       users_sent,
                       users_recieved
                   FROM
                   (
                   SELECT
                       toDate(time) as event_date,
                       gender,
                       age,
                       os,
                       user_id as user,
                       count() as messages_sent,
                       uniq(reciever_id) as users_sent
                    FROM
                        simulator.message_actions 
                    WHERE 
                        toDate(time) = '2022-01-26'
                    GROUP BY
                            event_date,
                            gender,
                            os,
                            age,
                            user
                    ) AS sent
                    FULL OUTER JOIN
                    (                      
                    SELECT
                       toDate(time) as event_date,
                       gender,
                       age,
                       os,
                       reciever_id as user,
                       count() as messages_recieved,
                       uniq(user_id) as users_recieved
                    FROM
                        simulator.message_actions
                    WHERE
                        toDate(time) = '2022-01-26'
                    GROUP BY
                        event_date,
                        gender,
                        age,
                        os,
                        user
                    ) AS recieve
                    USING user
                    format TSVWithNames"""
        df_cube = ch_get_df(query)
        return df_cube
        
    @task()
    def join_cubes(messages,feeds):
        final_cube = messages.merge(feeds, how='outer', on=['user', 'event_date', 'gender', 'age', 'os']).dropna()
        return final_cube

    @task()
    def transform_metric(df_cube, one_metric):
        full_metric_list = metric_list + [one_metric]
        group_metric_list = ['event_date'] + [one_metric]
        
        transformed_list = df_cube[full_metric_list]\
                                   .groupby(group_metric_list)\
                                   .sum()\
                                   .reset_index()
        return transformed_list
        
    @task()
    def load(gender, age, os):
        context = get_current_context()
        ds = context['ds']
        print(f'Metrics by os for date {ds}')
    
    @task()
    def load(gender, age, os):
        context = get_current_context()
        ds = context['ds']
        print(f'Metrics by os for date {ds}')
        print(os.to_csv(index=False, header=True, sep='\t'))
        print(f'Metrics by age for date {ds}')
        print(age.to_csv(index=False, sep='\t'))
        print(f'Metrics by gender for date {ds}')
        print(gender.to_csv(index=False, sep='\t'))
            
    df_cube_feed = extract_feed()
    df_cube_messages = extract_messages()
    full_cube = join_cubes(df_cube_feed, df_cube_messages)
        
    gender = transform_metric(full_cube, 'gender')
    age = transform_metric(full_cube, 'age')
    os = transform_metric(full_cube, 'os')
    load(gender, age, os)

dag_test = dag_sim_fin()
