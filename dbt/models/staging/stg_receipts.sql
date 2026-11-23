select receipt_id, po_line_id, received_date::date as received_date, received_qty from {{ source('raw', 'receipts') }}
