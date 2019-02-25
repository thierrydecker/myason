# -*- coding: utf-8 -*-

import dash
import dash_core_components as dcc
import dash_html_components as html
import sqlite3
import datetime


def get_data():
    con = sqlite3.connect("database/collector.db")
    with con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT
                seconds,
                SUM(packets),
                SUM(bytes),
                SUM(flows)
            FROM timeseries
            GROUP BY seconds
            ORDER BY seconds
            """,
        )
        timeseries = cur.fetchall()
        x = []
        y1 = []
        y2 = []
        y3 = []
        for point in timeseries:
            dt = datetime.datetime.fromtimestamp(point[0]).strftime('%Y-%m-%d %H:%M:%S')
            x.append(dt)
            y1.append(point[1])
            y2.append(point[2])
            y3.append(point[3])
    return x, y1, y2, y3


seconds, packets, octets, flows = get_data()

app = dash.Dash()
app.layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    [
                        dcc.Graph(
                            figure={
                                'data': [{'x': seconds, 'y': flows, 'type': 'line'}],
                                'layout': {
                                    'title': 'Flows'
                                },
                            }
                        ),
                    ],
                    className="six columns",
                ),
                html.Div(
                    [
                        dcc.Graph(
                            figure={
                                'data': [{'x': seconds, 'y': octets, 'type': 'line'}],
                                'layout': {
                                    'title': 'Bytes'
                                },
                            }
                        ),
                    ],
                    className="six columns",
                ),
                html.Div(
                    [
                        dcc.Graph(
                            figure={
                                'data': [{'x': seconds, 'y': packets, 'type': 'line'}],
                                'layout': {
                                    'title': 'Packets'
                                },
                            }
                        ),
                    ],
                    className="six columns",
                ),
            ],
            className="row",
        )
    ]
)
app.css.append_css({
    'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'
})

if __name__ == '__main__':
    app.run_server(debug=True)
