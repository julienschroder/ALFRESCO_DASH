import dash, os, itertools, flask
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
from pandas_datareader import data as web
from datetime import datetime as dt
import plotly.graph_objs as go
import pandas as pd
from random import randint
import plotly.plotly as py

server = flask.Flask(__name__)
server.secret_key = os.environ.get('secret_key', 'secret')
app = dash.Dash(name = __name__, server = server)
app.config.supress_callback_exceptions = True

#Data variables
cli = pd.read_pickle('Climate_full.p')
models_list = ['GFDL-CM3', 'GISS-E2-R', 'NCAR-CCSM4', 'IPSL-CM5A-LR','MRI-CGCM3']
web = 'https://www.snap.uaf.edu/webshared/jschroder/db/CSV/'
metrics = [ 'avg_fire_size','number_of_fires','total_area_burned']

#Function updating #1 plot => Alfresco plot
def get_data( models , scenarios, metric, domain, cumsum ) :
    metric = str(metric)
    domain = str(domain)
    def _get_metric_cumsum(lnk , cumsum ):
        #Extract, average and cumsum the raw data to a dataframe
        _df = pd.read_csv(lnk, index_col=0)
        _df = _df.ix[2006:].mean(axis = 1)
        if 'cumsum' in cumsum :
            _df = _df.cumsum(axis=0)
        else : pass
        return pd.Series.to_frame(_df)

    #Build the models full name and the link towards the CSV  <= todo build decent database but will do for now
    selection = [a[0]+ '_' + a[1] for a in itertools.product(models,scenarios)]
    if type(selection) is str : selection = [selection]
    rmt = [os.path.join(web, metric, "_".join(['alfresco', metric.replace('_',''), domain.title(), model, '1902_2100.csv' ])) for model in selection]

    #Extract dataframe and concat them together
    df_list = [_get_metric_cumsum(lnk , cumsum) for lnk in rmt]
    df = pd.concat(df_list,axis=1)
    df.columns=selection
    return  df


#Functions used to update #2 and #3 with climate data
def get_cli_data(models, scenarios, dictionnary):
    date = pd.date_range('2006','2101',freq='A-DEC')
    def _get_climate_annual(_df) :
        _df = _df[(_df.index.month >= 3 ) & (_df.index.month <= 9 )]
        _df1 = _df.resample("A-DEC").mean()["Boreal"]
        _df2 = pd.DataFrame(['NaN'] * len(date),date)
        _df3 = pd.concat([_df1 , _df2],axis=1)["Boreal"]
        return pd.Series.to_frame(_df3)

    #Build the full models name and extract the dataframe
    selection = [a[0]+ '_' + a[1] for a in itertools.product(models,scenarios)]
    if type(selection) is str : selection = [selection]
    df_list = [_get_climate_annual(dictionnary[model]) for model in selection]
    df = pd.concat(df_list,axis=1)
    df.columns=selection
    return  df




app.css.append_css({'external_url': 'https://cdn.rawgit.com/plotly/dash-app-stylesheets/2d266c578d2a6e8850ebce48fdb52759b2aef506/stylesheet-oil-and-gas.css'})  # noqa: E501

app.layout = html.Div(
    [
        html.Div(
            [
                html.H1(
                    'ALFRESCO Post Processing Outputs',
                    className='eight columns',
                ),
                html.Img(
                    src="https://www.snap.uaf.edu/sites/all/themes/snap_bootstrap/logo.png",
                    className='one columns',
                    style={
                        'height': '80',
                        'width': '225',
                        'float': 'right',
                        'position': 'relative',
                    },
                ),
            ],
            className='row'
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.P('Scenarios Selection :'),
                        dcc.Dropdown(
                            id='rcp',
                            options=[
                                {'label': 'RCP 45 ', 'value': 'rcp45'},
                                {'label': 'RCP 60 ', 'value': 'rcp60'},
                                {'label': 'RCP 85 ', 'value': 'rcp85'}
                            ],
                            multi=True,
                            value=[]
                        ),
                        html.P('Models Selection :'),
                        dcc.Dropdown(
                            id='model',
                            options=[{'label': a , 'value' : a} for a in models_list],
                            multi=True,
                            value=[]
                        ),
                        dcc.Checklist(
                            id='cumsum',
                            options=[
                                {'label': 'Cumulative Sum', 'value': 'cumsum'}
                            ],
                            values=[],
                        )
                    ],
                    className='six columns'
                ),
                html.Div(
                    [
                        html.P('Metric Selection:'),
                        dcc.Dropdown(
                            id='metric',
                            options=[{'label': a.replace('_',' ').title() , 'value' : a} for a in metrics],
                            value=None
                        ),
                        html.P('Domains Selection :'),
                        dcc.Dropdown(
                            id='domains',
                            options=[
                                {'label': 'Boreal', 'value': 'boreal'},
                                {'label': 'Tundra', 'value': 'tundra'}
                            ],
                            value=None
                        ),
                    ],
                    className='six columns'
                ),
            ],
            className='row'
        ),
        html.Div(
            [
                html.Div(
                    [
                        dcc.Graph(id='ALF')
                    ],
                    className='eleven columns'
                ),
            ],
        ),
        html.Div(
            [
                html.Div(
                    [
                        dcc.Graph(id='climate_tas')
                    ],
                    className='eleven columns'
                ),
            ],
        ),
        html.Div(
            [
                html.Div(
                    [
                        dcc.Graph(id='climate_pr')
                    ],
                    className='eleven columns'
                ),
            ],
        ),

    ],
    className='ten columns offset-by-one'
)

@app.callback(
    Output('ALF', 'figure'),
    [Input('model', 'value'),
    Input('rcp', 'value'),
    Input('metric', 'value'),
    Input('domains', 'value'),
    Input('cumsum', 'values')]
)
def update_graph(models, rcp, met_value, domain, cumsum):
    if (len(models) > 0 and len(rcp) > 0 and domain is not None and met_value is not None):
        df = get_data(models, rcp, met_value, domain, cumsum)
        if str(met_value) in ['total_area_burned','avg_fire_size'] :
            label = 'Area (km\u00b2)'
        else : label = 'Number of fires'

        return {
            'data': [{
                'x': df.index,
                'y': df[col],
                'name':col,
            } for col in df.columns],
            'layout' : go.Layout(
                        height=300,
                        margin= {'t': 20,'b':30 },
                        xaxis = {
                            'ticks' : 'outside',
                            'ticklen' : 5,
                            'showgrid' : False,
                            'linewidth' : 1,
                            'zeroline' : False,
                            'zerolinewidth' : 0
                        },
                        yaxis = {
                            'title' : label,
                            'ticks' : 'outside',
                            'ticklen' : 5,
                            'showgrid' : False,
                            'linewidth' : 1,
                            'zeroline' : False,
                            'zerolinewidth' : 0
                        },
                        showlegend=False)
        }

@app.callback(
    Output('climate_tas', 'figure'),
    [Input('model', 'value'),
    Input('rcp', 'value')
])
def update_tas(models, rcp):
    if (len(models) > 0 and len(rcp) > 0):
        df = get_cli_data(models, rcp, cli['tas'])

        return {
            'data': [{
                'x': df.index,
                'y': df[col],
                'name':col,
            } for col in df.columns],
            'layout' : go.Layout(
                        height=200,
                        margin= {'t': 20,'b':30 },
                        xaxis = {
                            'ticks' : 'outside',
                            'ticklen' : 5,
                            'showgrid' : False,
                            'linewidth' : 1,
                            'zeroline' : False,
                            'zerolinewidth' : 0
                        },
                        yaxis = {
                            'title' : "Temperature (\xb0C)",
                            'ticks' : 'outside',
                            'ticklen' : 5,
                            'showgrid' : False,
                            'linewidth' : 1,
                            'zeroline' : False,
                            'zerolinewidth' : 0
                        },
                        showlegend=False)
        }

@app.callback(
    Output('climate_pr', 'figure'),
    [Input('model', 'value'),
    Input('rcp', 'value')
])
def update_pr(models, rcp):
    if (len(models) > 0 and len(rcp) > 0):
        df = get_cli_data(models, rcp, cli['pr'])

        return {
            'data': [{
                'x': df.index,
                'y': df[col],
                'name':col
                }
                for col in df.columns],
                'layout' : go.Layout(
                            height=200,
                            margin= {'t': 20,'b':30 },
                            xaxis = {
                                'ticks' : 'outside',
                                'ticklen' : 5,
                                'showgrid' : False,
                                'linewidth' : 1,
                                'zeroline' : False,
                                'zerolinewidth' : 0
                            },
                            yaxis = {
                                'title' : 'Precipitation (mm)',
                                'ticks' : 'outside',
                                'ticklen' : 5,
                                'showgrid' : False,
                                'linewidth' : 1,
                                'zeroline' : False
                            },
                            showlegend=False)
        }



# Run the Dash app
if __name__ == '__main__':
    app.server.run()
