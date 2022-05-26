import datetime
import json
import time
from math import ceil

import pandas as pd
import requests
from google.cloud import bigquery
from loguru import logger
from tqdm import tqdm


def refresh_reservoir_levels(today):

    logger.info("getting UUIDs")
    client = BQClient()
    # get res uuids from tracking table
    uuid_df = client.get_uuids().set_index("uuid")

    logger.info("Updating {len(uuid_df)} uuids")

    update_data = []
    # for each uuids:
    for uuid, row in uuid_df.iterrows():

        # run an updating script
        update_data.append(client.update_reservoir_data(uuid, row["name"], today))

    return sum(update_data)


class WRISClient:
    def __init__(self):
        self.url = "http://wdo.indiawris.gov.in/api/reservoir/chart"

        self.data_columns = {
            "Current Year Level": "WATER_LEVEL",
            "Current Year Storage": "WATER_VOLUME",
            "Full Reservoir Level": "FULL_WATER_LEVEL",
        }

    def get_reservoir_data(self, sdate, edate, uuid):

        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "eDate": edate.strftime("%Y%m%d"),
            "format": "yyyyMMdd",
            "lType": "STATION",
            "pUUID": uuid,
            "sDate": sdate.strftime("%Y%m%d"),
            "src": "CWC",
        }

        response = requests.post(self.url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:

            data = json.loads(response.text)

            df = pd.DataFrame(
                index=data["labels"],
                data={vv["label"]: vv["data"] for vv in data["data"]},
            )

            df.index = pd.to_datetime(df.index)
            df.index.name = "DATETIME"

            df = df.rename(columns=self.data_columns).loc[
                :, list(self.data_columns.values())
            ]

            return df, response.status_code

        else:
            return None, response.status_code


class BQClient:
    def __init__(self):

        self.client = bigquery.Client()

        self.min_dt = datetime.datetime(2010, 1, 1)

        self.tracking_table = "oxeo-main.wave2web.tracked-reservoirs"

        self.reservoir_data_table = "oxeo-main.wave2web.reservoir-data"

    def check_errors(self, errors):

        if errors != []:
            raise ValueError(
                f"there where {len(errors)} error when inserting. " + str(errors),
            )

        return True

    def get_uuids(self):

        Q = f"""
            SELECT *
            FROM `{self.tracking_table}`
        """

        df = self.client.query(Q).result().to_dataframe()

        return df

    def track_reservoir(self, uuid, name, lake_wkt, upstream_wkt):

        errors = self.client.insert_rows_json(
            self.tracking_table,
            [
                {
                    "uuid": uuid,
                    "name": name,
                    "upstream_geom": upstream_wkt,
                    "lake_geom": lake_wkt,
                }
            ],
        )

        self.check_errors(errors)

        return True

    def get_most_recent_date(self, uuid):

        Q = f"""
            SELECT MAX(DATETIME)
            FROM `{self.reservoir_data_table}`
            WHERE RESERVOIR_UUID = '{uuid}'
        """

        df = self.client.query(Q).result().to_dataframe()

        return df.iloc[0]["f0_"].replace(tzinfo=None)

    def push_reservoir_data(self, df):

        errors = self.client.insert_rows_json(
            self.reservoir_data_table, df.reset_index().to_dict(orient="records")
        )

        self.check_errors(errors)

        return True

    def fill_period(self, uuid, name, start_dt, end_dt, sleep=None):

        wris_client = WRISClient()

        if (end_dt - start_dt).days > 30:

            n_calls = ceil((end_dt - start_dt).days / 30)

            logger.info(f"Filling data for {uuid}, {n_calls} api calls")

            all_data = []

            for ii in tqdm(range(n_calls)):

                df, status_code = wris_client.get_reservoir_data(
                    sdate=start_dt + datetime.timedelta(days=30 * ii),
                    edate=min(
                        start_dt + datetime.timedelta(days=30 * (ii + 1)), end_dt
                    ),
                    uuid=uuid,
                )

                if status_code == 200:

                    df["RESERVOIR_UUID"] = uuid
                    df["RESERVOIR_NAME"] = name

                    df.index = df.index.strftime("%Y-%m-%dT%H:%M:%S.%f")

                    # write to table
                    self.push_reservoir_data(df)

                    if sleep is not None:
                        time.sleep(sleep)

                    all_data.append(len(df))
                else:
                    all_data.append(0)

        else:

            logger.info(f"Filling data for {uuid}, 1 api call")

            df, status_code = wris_client.get_reservoir_data(
                sdate=start_dt, edate=end_dt, uuid=uuid
            )

            if status_code == 200:

                df["RESERVOIR_UUID"] = uuid
                df["RESERVOIR_NAME"] = name

                df.index = df.index.strftime("%Y-%m-%dT%H:%M:%S.%f")

                # write to table
                self.push_reservoir_data(df)

                all_data = [len(df)]
            else:
                logger.info(f"Status code: {status_code}, uuid={uuid},name={name}")
                all_data = [0]

        return all_data

    def update_reservoir_data(self, uuid, name, today, sleep=None):

        max_dt = self.get_most_recent_date(uuid)

        if pd.isna(max_dt):
            # empty data! -> fill from start_dt
            # filled_data = self.fill_period(uuid, name, self.min_dt, today, sleep)
            logger.info(f"No data for uuid={uuid},name={name}")
            filled_data = [0]

        else:
            # some data! -> fill from most recent
            filled_data = self.fill_period(
                uuid, name, max_dt + datetime.timedelta(days=1), today, sleep
            )

        return sum(filled_data)
