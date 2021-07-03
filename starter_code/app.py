#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
import json
from re import search
import dateutil.parser
import babel
import sys
import psycopg2
from os import error, name
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import FlaskForm as Form
from flask_migrate import Migrate
from sqlalchemy.orm import lazyload, subqueryload, joinedload
from sqlalchemy.sql.expression import false, join
from datetime import datetime
from flask_wtf.csrf import CSRFProtect
from models import db, Venue, Artist, Show
from forms import *
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#
def format_datetime(value, format='medium'):
  if isinstance(value, str):
        date = dateutil.parser.parse(value)
        if format == 'full':
          format="EEEE MMMM, d, y 'at' h:mma"
        elif format == 'medium':
          format="EE MM, dd, y h:mma"
        return babel.dates.format_datetime(date, format, locale='en')
  else:
        date = value
        if format == 'full':
          format = "EEEE MMMM, d, y 'at' h:mma"
        elif format == 'medium':
          format = "EE MM, dd, y h:mma"
        return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  for venue in db.session.query(Venue).all():
    data=[{'city':venue.city, 'state':venue.state,
    'venues':[{'id':venue.id, 'name':venue.name}]}] 
  return render_template('pages/venues.html', areas=data)

  
@app.route('/venues/search', methods=['POST'])
def search_venues():
  term = request.form.get('search_venues')
  result= db.session.query(Venue).filter(name == term).all()
  return render_template('pages/search_venues.html', results=result, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue= Venue.query.get_or_404(venue_id)
  past_shows = []
  upcoming_shows = []
  for show in venue.shows:
    temp_show = {
        'artist_id': show.artist_id,
        'artist_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': show.start_time.strftime("%m/%d/%Y, %H:%M")
    }
    if show.start_time <= datetime.now():
        past_shows.append(temp_show)
    else:
        upcoming_shows.append(temp_show)
  data=vars(venue)
  data['past_shows'] = past_shows
  data['upcoming_shows'] = upcoming_shows
  data['past_shows_count'] = len(past_shows)
  data['upcoming_shows_count'] = len(upcoming_shows)
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  form = VenueForm(request.form, meta={'csrf': False})
  if form.validate():
    try:
      venue = Venue()
      form.populate_obj(venue)
      db.session.add(venue)
      db.session.commit()       
      flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except:
      db.session.rollback()
      print(sys.exc_info())
      flash('An error occured. Venue ' + request.form['name'] + ' could not be listed!')
    finally:
      db.session.close()
  else:
    message = []
    for field, err in form.errors.items():
      message.append(field + ' ' + '|' .join(err))
    flash('Errors' + str(message))

  return render_template('pages/home.html')
  

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  Show.query.filter_by(venue_id=venue_id).delete()
  Venue.query.filter_by(id=venue_id).delete()
  
  return None

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = Artist.query.all()
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  data = request.form.get('search_venues')
  result= db.session.query(Artist).filter(Artist.name == data).all()
  return render_template('pages/search_artists.html', results=result, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id): 
  artist = Artist.query.get_or_404(artist_id)
  past_shows = []
  upcoming_shows = []
  for show in artist.shows:
    temp_show = {
        'venue_id': show.venue_id,
        'venue_name': show.venue.name,
        'venue_image_link': show.venue.image_link,
        'start_time': show.start_time.strftime("%m/%d/%Y, %H:%M")
    }
    if show.start_time <= datetime.now():
        past_shows.append(temp_show)
    else:
        upcoming_shows.append(temp_show)
  
  data=vars(artist)
  data['past_shows'] = past_shows
  data['upcoming_shows'] = upcoming_shows
  data['past_shows_count'] = len(past_shows)
  data['upcoming_shows_count'] = len(upcoming_shows)
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------

@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist= Artist.query.get_or_404(artist_id)
  form = ArtistForm(obj=artist)
  return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    form = ArtistForm(request.form)
    db.session.query(Artist).filter(Artist.id == artist_id).update({
      "name": form.name.data,
      "city" : form.city.data,
      "state" : form.state.data,
      "phone" : form.phone.data,
      "genres" : form.genres.data,
      "image_link" : form.image_link.data,
      "facebook_link" : form.facebook_link.data,
      "website" : form.website_link.data,
      "seeking_venue" : form.seeking_venue.data,
      "seeking_description" : form.seeking_description.data
    })
    db.session.commit()
    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get_or_404(venue_id)
  form = VenueForm(obj=venue)
  return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    form = VenueForm(request.form)
    db.session.query(Venue).filter(Venue.id == venue_id).update({
      "name": form.name.data,
      "address": form.address.data,
      "city" : form.city.data,
      "state" : form.state.data,
      "phone" : form.phone.data,
      "genres" : form.genres.data,
      "image_link" : form.image_link.data,
      "facebook_link" : form.facebook_link.data,
      "website" : form.website_link.data,
      "seeking_talent" : form.seeking_talent.data,
      "seeking_description" : form.seeking_description.data
    })
    db.session.commit()
    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  try:
    form = ArtistForm(request.form)
    artist = Artist()
    form.populate_obj(artist)
    db.session.add(artist)
    db.session.commit()       
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    print(sys.exc_info())
    flash('An error occured. Artist ' + request.form['name'] + ' could not be listed!')
  finally:
    db.session.close()
  return render_template('pages/home.html')

#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  data = db.session.query(Show).join(Artist.shows).order_by(Show.id).all()
  return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try:
    form = ShowForm(request.form)
    show= Show( artist_id=form.artist_id.data,
    venue_id=form.venue_id.data,
    start_time=form.start_time.data
      )
    db.session.add(show)
    db.session.commit()
    flash('Show was successfully listed!')
  except:
    db.session.rollback()
    print(sys.exc_info())
    flash('An error occurred. Show could not be listed.')
  finally:
    db.session.close()
  return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
