select carrier, site_id, standard_transit_days from {{ source('raw', 'carriers') }}
