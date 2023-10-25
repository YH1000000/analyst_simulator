SELECT date AS date,
       start_date AS start_date,
       max(active_users) AS "Users"
FROM
  (select toString(date) date, toString(start_date) start_date,
                               count(user_id) as active_users,
                               source
   from
     (select user_id,
             min(toDate(time)) as start_date,
             source
      from simulator_20230720.feed_actions
      group by user_id,
               source
      having start_date >= today()-20) t1
   join
     (select distinct user_id,
                      toDate(time) as date,
                      source
      from simulator_20230720.feed_actions) t2 using user_id
   group by date, start_date,
                  source) AS virtual_table
WHERE ((source = 'organic'))
GROUP BY date, start_date
LIMIT 1000;
