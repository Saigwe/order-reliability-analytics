select d::date as date_day, date_trunc('month', d)::date as month_start, year(d) as year, quarter(d) as quarter,
       isodow(d) as iso_weekday, strftime(d, '%b %Y') as month_label
from unnest(generate_series(date '2025-09-01', date '2027-01-31', interval 1 day)) as t(d)
