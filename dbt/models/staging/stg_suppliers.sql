select supplier_id, supplier_name, currency, invoice_uom from {{ source('raw', 'suppliers') }}
