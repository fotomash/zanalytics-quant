# Exporting Streamlit Dashboards to WordPress

1. Run `scripts/export_dashboards.sh` to export dashboards as static HTML.
2. The script copies the generated files into `wordpress/wp-content/uploads/dashboards/`.
3. Activate the **Zanalytics Dashboards** plugin in WordPress (`wordpress/wp-content/plugins/zanalytics-dashboards`).
4. Embed a dashboard on any page using `[zan_dashboard name="Home"]` where `Home` matches the exported filename.

Once uploaded, dashboards render at `info.zanalytics.app` via the shortcode.
