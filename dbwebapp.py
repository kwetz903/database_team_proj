import bottle
from mysql.connector import connect
from datetime import datetime, timedelta
import string 
# con = connect(user='bbdc8f82937ad0', password='371dc33d', database='heroku_17bb6a6cff89403', host='us-cdbr-iron-east-05.cleardb.net')

con = connect(user='root', password='Spring2017', database='wsoapp', host='158.158.240.230')
cursor = con.cursor()

new_service_form = """<html>
    <head>
    <title>Service Order Generator</title>
    <style>
    * {{
      font-family: sans-serif;
    }}
    ul{{
      padding-left: 0;
    }}
    li {{
      list-style-type: none;
      padding: 10px;
    }}
    h1{{
      text-align: center;
      color: #008fb3;
    }}
    #button{{
      text-align: center;    
    }}
    form{{
      text-align: right;
      max-width: 400px;
      margin: auto;
    }}
    form label{{
      float: left;
    }}
    form input, select {{
      width: 200px;
      height: 25px;
      padding: 3px 7px;
    }}
    #button input{{
      border-radius: 5px;
      border: none;
      height: 30px;
      background-color: #008fb3;
      width: 100px;
      color: white;
      
    }}
    .error{{
      color: red;
      text-align: center;
    }}
    .success{{
      color: green;
      text-align: center;
    }}
    </style>
    </head>
    <body>
      <h1>Service Order Generator</h1>
      {0}
      <form id="new_service_form" method="post" action="/">
        <ul>
          <li>
            <label>New Service Date*</label> 
            <input type='date' name='new_srvc_date' value='{3}'/>
          </li>
          <li>
            <label>New Service Time*</label> 
            <input type='Time' name='new_srvc_time' value='{4}'/>
          </li>
          <li> 
            <label>Template Service*</label>
            <select name="template_service" form="new_service_form">
              {1}
            </select>
          </li>
          <li> 
            <label>Title</label>
            <input type='text' name='title' value='{5}'/> 
          </li>
          <li> 
            <label>Theme</label>
            <input type='text' name='theme' value='{6}'/> 
          </li>
          <li> 
            <label>Songleader</label>
            <select name="songleader" form="new_service_form">
              {2}
            </select>
          </li>
        </ul>
        <div id="button"><input type='submit' value='Create'/></div>
      </form>
    </body>
    </html>"""
select_option_snippet = "<option value={0}>{1}</option>"
message_snippet = "<p class='{0}'>{1}</p>"

def get_form_select_options(service=None, songleader=None):
    """ gets valid template services and songleaders 
    returns (services: string, songleaders: string)
    use like: new_service_form.format(srvc_options = services, sgldr_options=songleaders)"""    
    # get service options
    services = ''
    cursor.execute("""
      SELECT Service_ID, Svc_DateTime
      FROM service
      """)
    service_records = cursor.fetchall()
    for row in service_records:
        service_id, service_datetime = row
        service_option = select_option_snippet.format(service_id, service_datetime)
        if str(service_id) == service:
          service_option = service_option.replace("<option", "<option selected")
        services = services + service_option
    # get songleader options
    songleaders = ''
    cursor.execute("""
      SELECT DISTINCT Person_ID, First_Name, Last_Name
      FROM person JOIN service ON person.Person_ID = service.Songleader_ID
      """)    
    songleader_records = cursor.fetchall()
    for row in songleader_records:
        person_id, person_first, person_last = row
        songleader_option = select_option_snippet.format(person_id, person_first + ' ' + person_last)
        if str(person_id) == songleader:
          songleader_option = songleader_option.replace("<option", "<option selected")
          print(songleader_option)
        songleaders = songleaders + songleader_option
    return (services, songleaders)

def check_for_service_datetime(service_datetime):
    """looks for a service with the new_service_datetime
    returns a bool indicating whether there's already a service with that datetime"""
    cursor.execute("""
      SELECT Svc_DateTime
      FROM service
      WHERE Svc_DateTime = %s
      """,(service_datetime,))
    service_records = cursor.fetchall()
    if service_records:
        return True
    else:
        return False

def make_service_events(template_service, new_service_time):
    """inserts a blanked out service event into the new service for each in the template service"""
    # get new service id
    new_service_id = None
    cursor.execute("""
      SELECT Service_ID
      FROM service
      WHERE Svc_DateTime = %s
      """, (new_service_time,))
    service_records = cursor.fetchall()
    for row in service_records:
        new_service_id = row

    #create service events
    cursor.execute("""
      INSERT INTO serviceevent (Service_ID, Seq_Num, EventType_ID, Confirmed)
      SELECT {0}, Seq_Num, EventType_ID, 'N' 
      FROM serviceevent
      WHERE Service_ID={1}
      """.format(new_service_id[0], template_service))

def post_render_form(msg, params):
    """formats page with data posted in form to keep user input"""
    services, songleaders = get_form_select_options(params['template_service'], songleader=params['songleader'])
    return new_service_form.format(
      msg, services, 
      songleaders, 
      params['new_srvc_date'], 
      params['new_srvc_time'], 
      params['title'], 
      params['theme']
    )


@bottle.post('/')
def create_service():
    # make sure they included the required information
    if bottle.request.params['new_srvc_date'] == '' or bottle.request.params['new_srvc_time'] == '' or bottle.request.params['template_service'] == '':
        msg = message_snippet.format("error","New Service Date, New Service Time, and Template Service are required") # TODO: keep user input
        return post_render_form(msg, bottle.request.params)
    # get new service datetime
    newsvc = datetime.strptime(bottle.request.params['new_srvc_date'], '%Y-%m-%d')
    splittime = string.split(bottle.request.params['new_srvc_time'],':')
    newtime = timedelta(hours=int(splittime[0]), minutes=int(splittime[1]))
    newtimestamp = newsvc + newtime
    print(newtimestamp)

    # check that new service datetime doesn't already exist
    new_timestamp_exists = check_for_service_datetime(newtimestamp)
    if new_timestamp_exists:
        msg = message_snippet.format("error","Service with that date and time already exists") # TODO: keep user input
        return post_render_form(msg, bottle.request.params)

    # get other attributes
    newtitle = '\'' + bottle.request.params['title'] + '\''
    newtheme = '\'' + bottle.request.params['theme'] + '\''
    newsongleader = bottle.request.params['songleader'] 
    timestamp = '\'' + newtimestamp.isoformat() + '\''

    # create service record
    cursor.execute("""
        INSERT INTO service (Service_ID, Svc_DateTime, Theme, Title, Notes, Organist_Conf, Songleader_Conf, Pianist_Conf, Organist_ID, Songleader_ID, Pianist_ID)
        VALUES(default, {0}, {1}, {2}, null, 'N', 'N', 'N', null, {3}, null)
        """.format(timestamp, newtheme, newtitle, newsongleader))

    # create service event records
    make_service_events(bottle.request.params['template_service'], newtimestamp)

    # save changes
    con.commit()
    msg = message_snippet.format("success","Service Successfully created") # TODO: keep user input
    return post_render_form(msg, bottle.request.params)


@bottle.get('/')
def service_form():
    # return form with db select options
    services, songleaders = get_form_select_options()
    return new_service_form.format('', services, songleaders, None, None, None, None)
	
if __name__ == "__main__":
    bottle.run(host="localhost", debug=True)