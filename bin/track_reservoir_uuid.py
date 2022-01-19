# a script that adds a reservoir uuid to the tracking table.
import click
from loguru import logger

from h2ox.reservoirs import BQClient

@click.group()
def cli():
    pass



@@cli.command()   
@click.argument('uuid')
@click.argument('name')
def track_reservoir(uuid,name):
    
    client = BQClient()
    
    # add reservoir to table
    client.track_reservoir(uuid, name)
    
    # fetch data from through time
    
    

if __name__=="__main__":
    cli()