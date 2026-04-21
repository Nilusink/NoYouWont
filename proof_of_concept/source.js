/*****************************************************************************
 * Created: 29.10.2020
 * Created by: JayR
 * Description: Get radar info
 * Notes:
 * Source:
 * ToDo: nothing
 * Version:  1.0
 * Changes:  1.0 - Initial creation
******************************************************************************/
/*****************************************************************************/

/********************************
 * Configuration
********************************/
/*****Default*****/
const LOGGING = true;   //if(LOGGING)   log('');                     //Log
const VERBOSE = false;  //if(LOGGING && VERBOSE)    log('');        //Verbose log
const STATE_PATH = '0_userdata.0.' + 'notification.radar.';
const STATES = ['lastMessage'];
/*****Custom*****/
const LATITUDE_START = 'XX.XXXXXX';
const LONGITUDE_START = 'XX.XXXXXX';
const LATITUDE_DEST = 'XX.XXXXXX';
const LONGITUDE_DEST = 'XX.XXXXXX';

//Radar
const BASE_URL = "https://cdn2.atudo.net/api/1.0/vl.php?type=0,1,2,3,4,5,6&box="

//Geocoding
const APIKEY_GEOCODING = '5b3bxxxxxxxxxxx2007a9d'; // https://opencagedata.com/

//Whatsapp
const WHATSAPP_STATE = 'whatsapp-cmb.0.sendMessage';
/********************************
 * Start/Init
********************************/
getRadarControll();

/********************************
 * Functions
********************************/

async function getRadarControll(){
    const radar = await getContent();
    let message = "";
    if(radar[0]!="empty") {
        if(LOGGING && VERBOSE)    log('The following radar conrolls was found: ' + JSON.stringify(radar));        //Verbose log
        message = "Die folgenden Biltzer wurden gefunden: ";
        for(let i=0;i<radar.length;i++){
                let addresse = await getAddress(radar[i].lat, radar[i].lng)
                message = message + "\n -" + addresse
        }
        if(LOGGING && VERBOSE)    log('Message: ' + message); //Verbose log
    } else {
        message = "No"
    }

    //Send Message
    const lastMessage = getState(STATE_PATH + 'lastMessage').val;
    if(lastMessage != message && message != "No") {
        setState(STATE_PATH + 'lastMessage', message);
        setState(WHATSAPP_STATE, message);
    }
    log(message);

    return message

}


function getContent(){
    return new Promise((resolve) => {
        const url = BASE_URL + LATITUDE_START + "," + LONGITUDE_START + "," + LONGITUDE_START + "," + LATITUDE_DEST  + "," + LONGITUDE_DEST
        request(url, function(err, response, json) {
            if(LOGGING && VERBOSE)    log('Content from radar API: ' + json); //Verbose log
            const myjson = JSON.parse(json).pois;

            if(json.length>25 && err==null){
                var myBlitzRes=[];
                for(let i=0;i<myjson.length;i++){
                    myBlitzRes.push({
                        lat: myjson[i].lat,
                        lng: myjson[i].lng,
                        radType: myjson[i].type,
                    });
                }
                resolve(myBlitzRes)
            }else{
                resolve(["empty"])
            }
        });
    });
}

function getAddress(lat, long) {
    return new Promise((resolve) => {
        let geoCodeUrl = 'https://api.opencagedata.com/geocode/v1/json'
        geoCodeUrl = geoCodeUrl + '?' + 'key=' + APIKEY_GEOCODING + '&q=' + lat + ',' + long + '&pretty=1'
        request(geoCodeUrl, function (err, response, json) {
            if (err==null){
                const myRes = JSON.parse(json).results[0].formatted;
                resolve(myRes)
            } else {
                resolve("Address resolution not possible")
            }
        });
    });
}


/********************************
 * Trigger
********************************/
schedule('2 * * * *', function() {
    getRadarControll();
});

/********************************
 * Create States
********************************/
STATES.forEach(function(STATE_NAME) {
    var STATE = STATE_PATH + STATE_NAME;
    if(!getObject(STATE)) {
        createState(STATE);
        if(LOGGING && VERBOSE) log('Create state: "' + STATE + '"');    //Verbose log
    }
});

/********************************
 * End
********************************/