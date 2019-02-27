from spider_blog import get_info, get_blog
import dash_core_components as dcc
import dash
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output
import datetime as dt
from sqlalchemy import create_engine
from flask_caching import Cache
import numpy as np


today = dt.datetime.today().strftime("%Y-%m-%d")  # 过去今天时间

engine = create_engine('sqlite:///blog.sqlite')
app = dash.Dash(__name__)
server = app.server

cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory'
})

# info = pd.read_sql('info', con=engine)
info = get_info()

############################color####################################

colors = ['0 255 127', '0 238 118', '0 205 102', '0 139 69', '192 255 62', '0 100 0', '152 251 152', '50 205 50',
          '0 255 0', '144 238 144']
color_scale = []
for color in colors:
    r, g, b = color.split(" ")
    color_scale.append("rgba({},{},{},{})".format(r, g, b, 0.6))
color_scale = color_scale*2

#######################################################################
# returns top indicator div
def indicator(color, text, id_value):
    return html.Div([
    html.P(text, className="twelve columns indicator_text"),
    html.P(id=id_value, className="indicator_value"),
], className="col indicator")

def get_news_table(data):
    df = data.copy()
    df.sort_values('read_num', inplace=True, ascending=False)
    titles = df['title'].tolist()
    urls = df['url'].tolist()
    read_num = df['read_num'].tolist()
    return html.Table([
        html.Tr([html.Th()])] + [
        html.Tr([
            html.Td(
                html.A(titles[i], href=urls[i], title=read_num[i], target="_blank",))
        ], style={'height': '30px', 'font-size': '16'})for i in range(min(len(df), 100))
    ], style={"height": "90%", "width": "98%"})

@cache.memoize(timeout=3590)
def get_df():
    df = pd.read_sql(today, con=engine)
    df['date_day'] = df['date'].apply(lambda x: x.split(' ')[0]).astype('datetime64[ns]')
    df['date_month'] = df['date'].apply(lambda x: x[:7].split('-')[0] + "年" + x[:7].split('-')[-1] + "月")
    df['weekday'] = df['date_day'].dt.weekday
    df['year'] = df['date_day'].dt.year
    df['month'] = df['date_day'].dt.month
    df['week'] = df['date_day'].dt.week
    return df

# header
head = html.Div([
    html.Div(html.Img(src=info['head_img'][0], height="100%"), style={"float": "left", "height": "100%"}),
    html.Span("{}博客的Dashboard".format(info['author_name'][0]), className='app-title'),
], className="row header")

columns = info.columns[3:]
col_name = ['文章数', '关注数', '喜欢数', '评论数', '等级', '访问数', '积分', '排名']
row1 = html.Div([
    indicator("#034011", col_name[i], col) for i, col in enumerate(columns)
], className='row')

row2 = html.Div([
    html.Div([
        html.P("每月文章写作情况"),
        dcc.Graph(id="bar", style={"height": "90%", "width": "98%"}, config=dict(displayModeBar=False),)
    ], className="col-4 chart_div",),
    html.Div([
        html.P("各类型文章占比情况"),
        dcc.Graph(id="pie", style={"height": "90%", "width": "98%"}, config=dict(displayModeBar=False),)
    ], className="col-4 chart_div"),
    html.Div([
        html.P("各类型文章阅读情况"),
        dcc.Graph(id="mix", style={"height": "90%", "width": "98%"}, config=dict(displayModeBar=False),)
    ], className="col-4 chart_div",)
], className='row')

years = get_df()['year'].unique()
select_list = ['每月文章', '类型占比', '类型阅读量', '每日情况']
dropDowm1 = html.Div([
    html.Div([
        dcc.Dropdown(id='dropdown1',
                 options=[{'label': '{}年'.format(year), 'value': year} for year in years],
                 value=years[1], style={'width': '40%'})
        ], className='col-6', style={'padding': '2px', 'margin': '0px 5px 0px'}),
    html.Div([
        dcc.Dropdown(id='dropdown2',
                 options=[{'label': select_list[i], 'value': item} for i, item in enumerate(['bar', 'pie', 'mix', 'heatmap'])],
                 value='heatmap', style={'width': '40%'})
        ], className='col-6', style={'padding': '2px', 'margin': '0px 5px 0px'})
], className='row')

row3 = html.Div([
    html.Div([
        html.P("每日写作情况"),
        dcc.Graph(id="heatmap", style={"height": "90%", "width": "98%"}, config=dict(displayModeBar=False),)
    ], className="col-6 chart_div",),
    html.Div([
        html.P("文章列表"),
        html.Div(get_news_table(get_df()), id='click-data'),
    ], className="col-6 chart_div", style={"overflowY": "scroll"})
], className='row')

app.layout = html.Div([
    dcc.Interval(id="stream", interval=1000*60, n_intervals=0),
    dcc.Interval(id="river", interval=1000*60*60, n_intervals=0),
    html.Div(id="load_info", style={"display": "none"},),
    html.Div(id="load_click_data", style={"display": "none"},),
    head,
    html.Div([
        row1,
        row2,
        dropDowm1,
        row3,
    ], style={'margin': '0% 30px'}),
])


@app.callback(Output('load_info', 'children'), [Input("stream", "n_intervals")])
def load_info(n):
    try:
        df = pd.read_sql('info', con=engine)
        return df.to_json()
    except:
        pass
@app.callback(Output('load_click_data', 'children'), [Input("river", "n_intervals")])
def cwarl_data(n):
    if n != 0:
        df_article = get_blog()
        df_article.to_sql(today, con=engine, if_exists='replace', index=True)


@app.callback(Output('bar', 'figure'), [Input("river", "n_intervals")])
def get_bar(n):
    df = get_df()
    df_date_month = pd.DataFrame(df['date_month'].value_counts(sort=False))
    df_date_month.sort_index(inplace=True)
    trace = go.Bar(
        x=df_date_month.index,
        y=df_date_month['date_month'],
        text=df_date_month['date_month'],
        textposition='auto',
        marker=dict(color=color_scale[:len(df_date_month)])
    )
    layout = go.Layout(
        margin=dict(l=40, r=40, t=10, b=50)
    )
    return go.Figure(data=[trace], layout=layout)

@app.callback(Output('pie', 'figure'), [Input("river", "n_intervals")])
def get_pie(n):
    df = get_df()
    df_types = pd.DataFrame(df['type'].value_counts(sort=False))
    trace = go.Pie(
        labels=df_types.index,
        values=df_types['type'],
        marker=dict(colors=color_scale[:len(df_types.index)])
    )
    layout = go.Layout(
        margin=dict(l=50, r=50, t=50, b=50)
    )
    return go.Figure(data=[trace], layout=layout)

@app.callback(Output('heatmap', 'figure'),
              [Input("dropdown1", "value"), Input('river', 'n_intervals')])
def get_heatmap(value, n):
    df = get_df()
    grouped_by_year = df.groupby('year')
    data = grouped_by_year.get_group(value)
    cross = pd.crosstab(data['weekday'], data['week'])
    cross.sort_index(inplace=True)
    trace = go.Heatmap(
        x=['第{}周'.format(i) for i in cross.columns],
        y=["星期{}".format(i+1) if i != 6 else "星期日" for i in cross.index],
        z=cross.values,
        colorscale="Greens",
        reversescale=True,
        xgap=4,
        ygap=5,
        showscale=False
    )
    layout = go.Layout(
        margin=dict(l=50, r=40, t=30, b=50),
    )
    return go.Figure(data=[trace], layout=layout)

@app.callback(Output('mix', 'figure'), [Input("river", "n_intervals")])
def get_mix(n):
    df = get_df()
    df_type_visit_sum = pd.DataFrame(df['read_num'].groupby(df['type']).sum())
    df['read_num'] = df['read_num'].astype('float')
    df_type_visit_mean = pd.DataFrame(df['read_num'].groupby(df['type']).agg('mean').round(2))
    trace1 = go.Bar(
        x=df_type_visit_sum.index,
        y=df_type_visit_sum['read_num'],
        name='总阅读',
        marker=dict(color=[color_scale[0]]*len(df_type_visit_sum)),
        yaxis='y',
    )
    trace2 = go.Scatter(
        x=df_type_visit_mean.index,
        y=df_type_visit_mean['read_num'],
        name='平均阅读',
        yaxis='y2',
        line=dict(color=color_scale[3])
    )
    layout = go.Layout(
        margin=dict(l=60, r=60, t=30, b=50),
        showlegend=False,
        yaxis=dict(
            side='left',
            title='阅读总数',
        ),
        yaxis2=dict(
            showgrid=False,  # 网格
            title='阅读平均',
            anchor='x',
            overlaying='y',
            side='right'
        ),
    )
    return go.Figure(data=[trace1, trace2], layout=layout)

@app.callback(Output('click-data', 'children'),
        [Input('pie', 'clickData'),
         Input('bar', 'clickData'),
         Input('mix', 'clickData'),
         Input('heatmap', 'clickData'),
         Input('dropdown1', 'value'),
         Input('dropdown2', 'value'),
         ])
def display_click_data(pie, bar, mix, heatmap, d_value, fig_type):
    try:
        df = get_df()
        if fig_type == 'pie':
            type_value = pie['points'][0]['label']
            # date_month_value = clickdata['points'][0]['x']
            data = df[df['type'] == type_value]
        elif fig_type == 'bar':
            date_month_value = bar['points'][0]['x']
            data = df[df['date_month'] == date_month_value]
        elif fig_type == 'mix':
            type_value = mix['points'][0]['x']
            data = df[df['type'] == type_value]
        else:
            z = heatmap['points'][0]['z']
            if z == 0:
                return None
            else:
                week = heatmap['points'][0]['x'][1:-1]
                weekday = heatmap['points'][0]['y'][-1]
                if weekday == '日':
                    weekday = 6
                year = d_value
                data = df[(df['weekday'] == int(weekday)-1) & (df['week'] == int(week)) & (df['year'] == year)]
        return get_news_table(data)
    except:
        return None

def update_info(col):
    def get_data(json, n):
        df = pd.read_json(json)
        return df[col][0]
    return get_data

for col in columns:
    app.callback(Output(col, "children"),
                 [Input('load_info', 'children'), Input("stream", "n_intervals")]
     )(update_info(col))


external_css = [
    "https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css",
    "https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",
    "http://raw.githack.com/ffzs/DA_dash_hr/master/css/my.css",
]

for css in external_css:
    app.css.append_css({"external_url": css})


if __name__ == '__main__':
    app.run_server(debug=True, threaded=True, port=7777)