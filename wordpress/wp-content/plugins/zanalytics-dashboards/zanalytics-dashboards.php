<?php
/*
Plugin Name: Zanalytics Dashboards
Description: Provides a shortcode to embed exported Streamlit dashboards from uploads/dashboards.
Version: 0.1
Author: Zanalytics
*/

function zan_dashboard_shortcode($atts) {
    $atts = shortcode_atts(array(
        'name' => 'Home',
        'height' => '800px'
    ), $atts, 'zan_dashboard');

    $src = content_url('uploads/dashboards/' . $atts['name'] . '.html');
    $iframe = sprintf(
        '<iframe src="%s" style="width:100%%;height:%s;border:0;" loading="lazy"></iframe>',
        esc_url($src),
        esc_attr($atts['height'])
    );
    return $iframe;
}
add_shortcode('zan_dashboard', 'zan_dashboard_shortcode');
?>
