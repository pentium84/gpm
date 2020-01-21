# -*- coding: UTF-8 -*-
import csv
import io
import os
import time

import pandas as pd
import geocoder
import requests
from gpm.utils import ADRESS_COL_NAME, add_adress
from termcolor import colored

from gpm.decorators import simple_time_tracker

from arcgis.gis import GIS
from arcgis.geocoding import get_geocoders, batch_geocode

# Arcgis API
pwd = "Pim62Z_pZm49Ver"
username = "lologibus2"

# Bing API
bing_key = "AkD8xlCWJPLgo3TmNt8DokHix1klCyhw50IpR0mR7mrn9Ee0eS4Gmi6ajSZjDMyg"

# HERE API
# lologibus77@gmail.com
here_app_id = "L9A8g1WqFIETCd5pyC3c"
here_app_key = "t6e-UcwJ8O9GaaDKTSAZAA"


def processs_geojson(g):
    """
    get information from geocoder
    :param g: geocoder instance
    :return:
    """
    # print('\n')
    if g.ok:
        res = str(g.osm['y']) + ',' + str(g.osm['x'])
    else:
        res = ','
    # print(colored(res, 'blue'))
    return res


class geo_coder(object):
    """
    geocoder returning (lat, lng) from address
    either online or offline
    """

    def __init__(self, kind='arcgis', offline=False):
        self.options = ['osm', 'here', 'arcgis', 'bing']
        self.kind = kind
        self.offline = offline

    # @simple_time_tracker
    def geocode(self, address, session):
        # url = 'http://localhost/nominatim/'
        if self.offline:
            url = 'localhost'
            self.g = geocoder.osm(address, url=url, session=session)
        if self.kind == 'arcgis':
            self.g = geocoder.arcgis(address, session=session)
        if self.kind == 'here':
            self.g = geocoder.here(address, session=session, app_id=here_app_id, app_code=here_app_key)
        if self.kind == 'bing':
            self.g = geocoder.bing(address, session=session, key=bing_key)
        res = processs_geojson(self.g)
        return res

    def run(self, addresses):
        """
        extract city, Country, and
        :return:
        """
        res = []
        l_addresses = [addresses] if type(addresses) != list else addresses
        with requests.Session() as session:
            for address in l_addresses:
                res.append(self.geocode(address, session))
        return res


##################################
#  Batch geocoding
##################################

@simple_time_tracker
def batch_geocode(l_adress, kind='arcgis'):
    if kind == 'arcgis':
        gis = GIS("http://www.arcgis.com", username=username, password=pwd)
        # use the first of GIS's configured geocoders
        geocoder = get_geocoders(gis)[0]
        results = batch_geocode(l_adress)
        lats = [r['location']['x'] for r in results]
        lngs = [r['location']['y'] for r in results]
        return lats, lngs

@simple_time_tracker
def batch_geocode_gouv(csv_path='gpm/data/test_batch_api.csv', sep=',', df=None,
                       l_cols=['num_niv_type_voie', 'cd_postal', 'nom_ville']):
    """
    geocode from gouv opendata API, only working for french geoloc
    advantages : free, no limit, and faster
    disadvantages : only for France
    :param csv_path:
    :param save:
    :param sep:
    :return: same df with 2 new cols (lat, lng)
    """
    url = "https://api-adresse.data.gouv.fr/search/csv"
    if type(df) == pd.core.frame.DataFrame:
        cols = list(df)
        if ADRESS_COL_NAME not in list(df):
            df = add_adress(df=df, l_cols=l_cols)
        transit_csv_name = 'DataReformated_ApiGouv.csv'
        df[[ADRESS_COL_NAME]].to_csv(transit_csv_name, index=False, sep=sep)
        csv_path = transit_csv_name
    else:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=sep)
            cols = reader.fieldnames
    # Send request to gouv api
    with open(csv_path, 'rb') as f:
        res = requests.post(url, files={'data': f})
    # Format output file
    df_res = pd.read_csv(io.StringIO(res.text), sep=',')
    new_cols = ['latitude', 'longitude']
    df[new_cols] = df_res[new_cols]
    df = df.filter(items=cols+new_cols)
    df.rename(columns={"latitude": "lat", "longitude": "lng"}, inplace=True)
    os.remove(transit_csv_name)
    return df


if __name__ == '__main__':
    test_stream=False
    add = ["34 rue Raynouard 75016 Paris", "11 rue d'Hauteville 75010 Paris", "110 rue de Rivoli, Paris"]
    l_geocoders = ['here', 'arcgis', 'bing']
    for kind in l_geocoders:
        if test_stream:
            print(colored(kind, "green"))
            gecod = geo_coder(offline=False, kind=kind)
            res = gecod.run(add)
            print('\n')
    # Batch api gouv geocoding
    file2 = "data2_code"
    datapath = "/Users/jeanbizot/Documents/projets/GROUPAMA/gpm/gpm/data"
    file_path = '{}/{}.csv'.format(datapath, file2)
    sep = ';'
    df = pd.read_csv(file_path, sep=sep)
    df['cd_postal'] = df['Code postal']
    res = {}
    for N in [100, 1000, 10000, 100000]:
        print(N)
        tic = time.time()
        df_res = batch_geocode_gouv(df=df.head(N), sep=sep)
        res[N] = time.time() - tic

