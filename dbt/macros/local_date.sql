{# UTC timestamp -> local calendar date at a site with a fixed UTC offset (hours). #}
{% macro local_date(ts, offset) -%}
    cast({{ ts }} + to_hours(cast({{ offset }} as integer)) as date)
{%- endmacro %}
