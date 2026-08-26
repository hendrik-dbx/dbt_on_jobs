{#
    Use the model's custom schema name verbatim (e.g. `silver`, `gold`, `bronze`)
    instead of dbt's default behaviour of prefixing it with the target schema.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
