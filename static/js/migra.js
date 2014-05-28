/* migra.js */

//first, checks if it isn't implemented yet
if (!String.prototype.format) {
    String.prototype.format = function() {
        var args = arguments;
        return this.replace(/{(\d+)}/g, function(match, number) {
            return typeof args[number] != 'undefined'
            ? args[number]
            : match
            ;
        });
    };
}

if (!String.prototype.repeat) {
    String.prototype.repeat = function(n) {
        return new Array(isNaN(n) ? 1 : ++n).join(this);
    }
}

MigraForms = { Intro: { Value: 'Intro', Switches: [ true, true, false, false, false ] },
UploadForm: { Value: 'Upload', Switches: [ true, false, true, false, false ] },
FilterForm: { Value: 'Filter', Switches: [ true, false, false, true, false ] },
WalkForm: { Value: 'Walk', Switches: [ true, false, false, false, true ] },
View: { Value: 'View', Switches: [ false, false, false, false, false ] }
};
MigraPopups = { Help: '#popup_help', Info: '#popup_info', About: '#popup_about' };

function initialize()
{
    //initialize our stuff: the map, its constituent thingies
    var myOptions = {
        zoom: 3,
        center: new google.maps.LatLng(30,-60),
        mapTypeId: google.maps.MapTypeId.ROADMAP
    };

    //Do not define these at all.
    window.data = null;
    window.overlays = null;
    window.options = {};

    window.stat = new MigraStatus();
    window.stat.actionStart ("Initializing")
    //the map has a few goodies.
    window.map = new google.maps.Map(document.getElementById('map_canvas'), myOptions);
    window.clusterer = new MarkerClusterer ( window.map, [], { maxZoom: 10 } );
    window.geocoder = new google.maps.Geocoder();
    window.spiderifier = new OverlappingMarkerSpiderfier(window.map);
    window.mapper = new Mapper();

    //initialize all the map variables
    clearMap();
    addEventListeners();

    window.stat.actionEnd("Initialized");
    showForm(MigraForms.Intro);
}

function MigraStatus ()
{
    //Various status feedback functions

    this.actionStart = function(desc)
    {
        this.info(desc + "...");
        $('#spinner').show();
    }

    this.actionUpdate = function(i,total)
    {
        if ( total = 0 ) return;

        var progressBar = document.getElementById("progressBar");
        var percentageDiv = document.getElementById("percentageCalc");

        progressBar.max = total;
        progressBar.value = i;
        percentageDiv.innerHTML = Math.round(i / total * 100) + "%";

        return;
    }

    this.actionEnd = function(msg)
    {
        if ( typeof(msg) != "undefined" ) this.info(msg + ".");
        $('#spinner').hide();
    }

    this.actionError = function(msg)
    {
        this.error("Error: " + msg + ".");
        $('#spinner').hide();
    }

    this.info = function(msg)
    {
        //show progress on the bar. log the same message.
        $("#message_pad").text (msg);
        console.log(msg);
    }

    this.warning = function(msg)
    {
        $("#message_pad").text (msg);
        console.log(msg);
    }

    this.error = function(msg)
    {
        $("#message_pad").text (msg);
        console.log(msg);
        window.alert ( msg );
    }
}

function Address ( placename, latlng )
{
    //Address class. Placename coupled with a google maps LatLng object
    this.placename = placename;
    this.latlng = latlng;
    this.people = [];

    this.addPerson = function(person)
    {
        this.people.push ( person );
    }

    this.cache = function()
    {
        try {
            var req = { name: this.placename, lat: this.latlng.lat(), lng: this.latlng.lng() };
            $.post('/cache', req, function() { }, "json"  );
        } catch ( e ) {
            window.stat.warning ( "Failed to cache {0} at ({1}, {2}): {3}", req.name, req.lat, req.lng, e.toString() );
        }
    }

    this.draw = function ()
    {
        for (var i = 0; i < this.people.length; i++) {
            this.people[i].latlng = this.latlng;
            this.people[i].draw();
        }
    }

    this.map = function ( )
    {
    }
}

function Mapper ( )
{

    this.locationStatus = { cache: 0, total: 0, geocoded: 0, error: 0 };

    this.reset = function ()
    {
        this.locationStatus.total =  Object.keys(window.data.addresses).length;
        this.locationStatus.geocoded = 0;
        this.locationStatus.cache = 0;
        this.locationStatus.error = 0;
    }

    this.__progressFunctionLocations = function()
    {
        if ( this.locationStatus.geocoded + this.locationStatus.cache + this.locationStatus.error >= this.locationStatus.total )
        {
            window.stat.actionEnd();
            window.stat.info ( "Mapped {0} individuals at {4} distinct locations ({1} geocoded and cached, {2} retrieved from cache, {3} errors).".format ( Object.keys(window.data.people).length, this.locationStatus.geocoded, this.locationStatus.cache, this.locationStatus.error, this.locationStatus.total ) );
            this.drawMissingLinks();
        } else {
            window.stat.actionUpdate(this.locationStatus.geocoded + this.locationStatus.error, this.locationStatus.total - this.locationStatus.cache);
        }
    }

    this.drawMissingLinks = function ( ) {
        //When this happens we need to go find the links that have not been drawn
        for ( var i=0; i < window.data.links.length; i ++ )
        {
            l = window.data.links[i];
            if ( ! l.drawn ) {
                l.resolveMissingLink();
            }
        }
    }

    this.map = function (address)
    {
        if ( address.latlng != null )
        {
            //We're already done.
            address.draw();
            this.locationStatus.cache ++;
            this.__progressFunctionLocations();
        }
        else
        {
            window.geocoder.geocode( { 'address': address.placename }, function ( results, status ) {
                //window.mapper below is essentially this
                if (status == google.maps.GeocoderStatus.OK )
                {
                    window.stat.info ( "Geocoded {0}.".format(address.placename) );
                    address.latlng = results[0].geometry.location;
                    address.draw();
                    address.cache();
                    window.mapper.locationStatus.geocoded ++;
                }
                else if (status == google.maps.GeocoderStatus.OVER_QUERY_LIMIT)
                {
                    setTimeout(function() {window.mapper.map(address); }, Math.random() * 10000 );
                }
                else
                {
                    window.stat.warning ( "Error finding {0}: {1}.".format ( address.placename , status ) );
                    window.mapper.locationStatus.error ++;
                }
                window.mapper.__progressFunctionLocations();
            } );
        }
    }
}

function AncestryLink ( parentID, childID )
{
    //A link between parent and child
    this.parent = window.data.people[parentID];
    window.data.people[parentID].addChildLink(this);

    this.child = window.data.people[childID];
    window.data.people[childID].addParentLink(this);

    this.drawn = false;

    this.draw = function ( ) {
        //Draw may be called three times on this link. The first time when it is established, and then
        //When the location at each end is established.
        //If there is no place name or the latlng cannot be established then we draw "virtual" lines to the ancestors.

        if ( this.parent.latlng === undefined || this.parent.latlng == null ) return;
        if ( this.child.latlng === undefined  || this.child.latlng == null ) return;

        this.drawOne ( this.parent, this.child );
        this.drawn = true;
    }

    this.resolveMissingLink = function ( ) {
        //Make sure we haven't been drawn.
        if ( this.drawn ) return;

        var ancestors = [];
        var descendants = [];

        if ( this.parent.latlng === undefined  || this.parent.latlng == null )
        {
            //If parent does not have a lat/lng then
            ancestors = this.parent.findAncestorsWithLocation(0);
        } else {
            ancestors = [ this.parent ];
        }

        if ( this.child.latlng === undefined  || this.child.latlng == null )
        {
            descendants = this.child.findDescendantsWithLocation(0);
        } else {
            descendants = [ this.child ];
        }

        for ( var a=0; a < ancestors.length; a++ ) {
            for ( var d=0; d < descendants.length; d++ ) {
                this.drawOne ( ancestors[a], descendants[d] );
                //                console.log ( "Creating link from {0} to {1} spanning {2} generation(s)".format ( ancestors[a].name, descendants[d].name, ancestors[a].generation - descendants[d].generation ) );
            }
        }

        this.drawn = true;

    }

    this.drawOne = function ( p, c )
    {
        var maxWeight = window.options["depth"];
        var lineOpacity = 0.5;
        var weight = Math.abs ( maxWeight - Math.min ( p.generation, maxWeight - 1 ) );
        if ( weight < 1 || weight === undefined || weight == NaN || weight == null ) weight = 1;

        var icons = null;

        if ( p.generation - c.generation > 1 )
        {
            lineOpacity = 0;
            icons = [{
                icon: {
                    path: 'M 0,-1 0,1',
                    strokeOpacity: 0.3,
                    strokeWeight: weight,
                    scale: 4
                },
                offset: '0',
                repeat: '15px'
            }];
        }

        var plOptions = {
            path: [ p.latlng, c.latlng ],
            strokeWeight: weight,
            geodesic: true,
            strokeOpacity: lineOpacity,
            strokeColor: this.getStrokeColor(),
            map: window.map,
            link: this,
            icons: icons
        };

        var pl = new google.maps.Polyline(plOptions);
        window.overlays.polylines.push ( pl );

        //On click show path from this person to the focal individual
        google.maps.event.addListener(pl, 'click', function() {
            this.link.parent.showPathToFocus ( );
        });
    }

    this.getStrokeColor = function() {

        var colors = { M: 0, F: 0 }

        for ( i = 1; i < this.parent.path.length; i ++ ) {
            colors[window.data.people[this.parent.path[i]].sex] += ( 1 / Math.pow(2,i) );
        }
        colors[this.parent.sex] += ( 1 / Math.pow(2,this.parent.path.length) );

        bluefactor = Math.round(colors["M"] * 255).toString(16);
        redfactor = Math.round(colors["F"] * 255).toString(16);
        greenfactor = Math.round(Math.min(colors["M"],colors["F"])*255).toString(16);

        bluefactor = "0".repeat(2-bluefactor.length) + bluefactor;
        redfactor = "0".repeat(2-redfactor.length) + redfactor;
        greenfactor = "0".repeat(2-greenfactor.length) + greenfactor;

        strokeColor = "#{0}{1}{2}".format ( redfactor,greenfactor,bluefactor );

        return strokeColor

    }


}

function Person ( jsonPerson )
{
    //Give a json person, turn it into "our" person. more or less the same but automatically gets latlng
    this.id = jsonPerson["id"];
    this.name = jsonPerson["name"];

    this.generation = jsonPerson["generation"];
    this.sex = jsonPerson["sex"];
    this.path = jsonPerson["path"];
    try
    {
        this.date = jsonPerson["location"]["date"];
        this.placename = jsonPerson["location"]["name"];
    }
    catch ( e )
    {
        this.date = null;
        this.placename = null;
    }

    window.data.people[this.id] = this;

    this.sexratio = 0;
    this.parentLinks = [];
    this.childLinks = [];

    if ( ! this.placename ) {
        this.latlng = null;
    } else {
        if ( window.data.addresses[this.placename] === undefined )
        {
            this.latlng = ( jsonPerson["location"]["latlng"] == null ) ? null : new google.maps.LatLng(jsonPerson.location.latlng.lat, jsonPerson.location.latlng.lng);
            window.data.addresses[this.placename] = new Address ( this.placename, this.latlng );
        }

        window.data.addresses[this.placename].addPerson(this);
    }

    //add a link to this person.
    this.addParentLink = function ( link ) {
        this.parentLinks.push ( link );
    }

    this.addChildLink = function ( link ) {
        this.childLinks.push ( link );
    }

    this.showPathToFocus = function ( ) {
        var path = [];
        var tempMarkers = [];
        //        var s = new OverlappingMarkerSpiderfier(map);

        //we are going to hide all links and just show the path from this individual to the focus individual.
        showAllOverlays(false);

        var curLink = this.childLinks[0];
        var m = curLink.parent.addMarker();
        //        s.addMarker(m);
        tempMarkers.push ( m );
        path.push ( curLink.parent.latlng );
        while ( curLink && curLink.child ) {
            m = curLink.child.addMarker();
            tempMarkers.push ( m );
            //            s.addMarker(m);
            if ( curLink.child.latlng ) path.push (curLink.child.latlng);
            curLink = curLink.child.childLinks[0]; //There should only be one.
        }

        var plOptions = {
            path: path,
            geodesic: true,
            strokeColor: "orange",
            weight: 4,
            map: window.map,
            points: tempMarkers
            //            spider: s
        };

        newLine = new google.maps.Polyline(plOptions)

        //When this new line is clicked, return everything to its original state
        google.maps.event.addListener(newLine, 'click', function() {
            this.setMap(null);
            //            s.setMap(null);
            for ( j = 0; j < tempMarkers.length; j ++ )
            {
                tempMarkers[j].setMap(null);
            }
            showAllOverlays(true);
        });
    }


    this.addMarker = function ( )
    {

        pinColor = this.sex == "F" ? "FF8888" : "8888CC";
        var markerCharacter = "?";
        switch ( this.generation )
        {
        case 0:
            markerCharacter = "%E2%80%A2";
            break;
        case 1:
            markerCharacter = ( this.sex == "F" ? "M" : "F" );
            break;
        case 2:
            markerCharacter = "G";
            break;
        default:
            markerCharacter = this.generation - 2;
        }

        var markerOpts = {
            position: this.latlng,
            map: window.map,
            icon: new google.maps.MarkerImage("http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=" + markerCharacter + "|" + pinColor),
            title: "{0} ({1}; {2}; {3})".format( this.name , getRelationshipDesc(this) , this.placename , this.date, this.sexratio ),
            person: this
        };

        return new google.maps.Marker ( markerOpts );

    }

    this.draw = function () {
        m = this.addMarker ();
        this.marker = m;
        window.overlays.markers.push ( m );
        window.clusterer.addMarkers ( [ m ] );
        window.spiderifier.addMarker ( m );

        //now we see if we have locations on both ends of the given link.
        for (var j = 0; j < this.childLinks.length; j++) {
            this.childLinks[j].draw();
        }
        for (var j = 0; j < this.parentLinks.length; j++) {
            this.parentLinks[j].draw();
        }

    }

    this.findAncestorsWithLocation = function(l) {
        if ( l > 10 ) return [ this ];

        if ( this.latlng !== undefined && this.latlng != null ) {
            return [this];
        }

        var result = [];
        for ( var i=0; i < this.parentLinks.length; i++ ) {
            var a = this.parentLinks[i].parent.findAncestorsWithLocation(l+1);
            for ( var j=0; j < a.length; j++ ) {
                result.push(a[j]);
            }
        }

        return result;
    }

    this.findDescendantsWithLocation = function(l) {
        if ( l > 10 ) return [ this ];

        if ( this.latlng !== undefined && this.latlng != null ) {
            return [this];
        }

        var result = [];
        for ( var i=0; i < this.childLinks.length; i++ ) {
            var d = this.childLinks[i].child.findDescendantsWithLocation(l+1);
            for ( var j=0; j < d.length; j++ ) {
                result.push(d[j]);
            }
        }

        return result;
    }


}

//reset the map.
function clearMap()
{

    if ( window.overlays != null ) {
        for (var i = 0; i < window.overlays.markers.length; i++ )
        {
            window.overlays.markers[i].setMap(null);
        }

        for (var i = 0; i < window.overlays.polylines.length; i++ )
        {
            window.overlays.polylines[i].setMap(null);
        }
    }

    window.data = { people: [], addresses: [], links: [] };
    window.overlays = { markers: [], polylines: [] };

    window.clusterer.clearMarkers();

}

function addEventListeners()
{

    $('#btn_start').click(function(e) {
        showForm(MigraForms.UploadForm);
    });

    //When our forms are submitted we want to process their forms. When those are done we want to do things.
    $('#upload_form').submit(function (e) {
        window.stat.actionStart("Uploading data");
        processForm(this, e,function (result) {
            window.stat.actionEnd("Data uploaded");
            showForm(MigraForms.FilterForm);
        });
    });

    //When our forms are submitted we want to process their forms. When those are done we want to do things.
    $('#filter_form').submit(function (e) {
        window.stat.actionStart("Filtering list of individuals");
        processForm(this, e,function (result) {
            try
            {
                buildPeopleList(result);
                window.stat.actionEnd("List of people built");
            }
            catch ( e )
            {
                window.stat.error ( "Error filtering: {0}.".format(e.toString()) );
                showForm ( MigraForms.FilterForm );
            }
        });
    });

    $('#walk_form').submit(function (e) {
        window.stat.actionStart("Walking the genealogy");
        processForm(this, e,function (result) {
            window.stat.actionStart("Genealogy walked. Drawing map");
            try
            {
                drawMap(result);
            }
            catch ( e )
            {
                window.stat.error ( "Error walking: {0}.".format(e.toString()) );
                showForm ( MigraForms.FilterForm );
            }
        });
    });

    $('#reset_form').submit(function (e) {
        clearMap();
    });

    $('#btn_restart').click(function(e) {
        //Might need to clean up data
        showForm(MigraForms.UploadForm);
    });

    $('#btn_choose').click(function(e) {
        showForm(MigraForms.FilterForm);
    });

    $('#btn_help').click(function(e) {
        showPopup(MigraPopups.Help);
    });

    $('#btn_about').click(function(e) {
        showPopup(MigraPopups.About);
    });

    $('.popup_closer').click(function(e) {
        hidePopups();
    });

}

function hidePopups()
{
    $('#popup_info').hide();
    $('#popup_help').hide();
    $('#popup_about').hide();
}


function showPopup ( n )
{
    e = [ '#popup_info', '#popup_help', '#popup_about' ];

    for ( var i = 0; i < e.length; i++ )
    {
        if ( n == e[i] ) { $(e[i]).show(); } else { $(e[i]).hide(); }
    }
}

function showForm ( f )
{
    e = [ '#overlay', '#intro', '#upload_form_wrapper', '#filter_form_wrapper', '#walk_form_wrapper' ];

    for ( var i = 0; i < e.length; i ++ )
    {
        if ( f.Switches[i] ) { $(e[i]).show(); } else { $(e[i]).hide(); }
    }
}

function processForm(form, e, successfunction )
{
    //I like this function. Generically takes a form and submits the data via AJAX post.
    //I found the basics on stackoverflow and then tweaked it for my needs
    e.preventDefault();
    //I don't even need these variables.
    var formData = new FormData(form);
    form_action = $(form).attr('action');

    $.ajax({
        type: 'post',
        beforeSend: function() {
            //before we send, disable the form so we cant' submit twice
            $(form).find(":input").prop('disabled',true);
        },
        complete: function() {
            //this event fires whether successful or not. enable everything again (it may get hidden)
            $(form).find(":input").prop('disabled',false);
        },
        xhr: function () {
            //The XMLHTTPRequest sends notifications as a file is uploaded. That's nice.
            myXhr = $.ajaxSettings.xhr();
            if (myXhr.upload) {
                myXhr.upload.addEventListener('progress', function(evt) { window.stat.actionUpdate(evt.loaded,evt.total); }, false);
                myXhr.upload.addEventListener('load', function(evt) { window.stat.actionStart("Server processing data"); } );
            }
            return myXhr;
        },
        data: formData,
        url: form_action,
        processData: false,
        contentType: false,
        dataType: 'json',
        success: successfunction,
        error: function( xhr, httpStatus, msg ) {
            window.stat.error ( "Error in AJAX request: ({0}): {1}.".format( httpStatus , msg ) );
        }
    });
}

function buildPeopleList(httpData)
{
    //Given the Json returned from our "p" action, build the list of people around whom we can build our map.
    var value = "";
    var i = 0;
    window.options = httpData.parameters;

    $('#i_select').empty();

    if ( httpData.people.length > 0 )
    {
        //We have found at least one match.
        $.each(httpData.people, function(key, person) {
            i++;
            window.stat.actionUpdate(i,httpData.people.length);
            value = "{0} {1}".format( person.name, person.birth ? " (b. " + person.birth.date + ")" : "" );
            $('#i_select')
            .append($('<option>', { value : person.id,
                text: "{0} {1}".format( person.name, person.birth ? " (b. {0})".format(person.birth.date) : "" ) }

            ));
        });
        showForm(MigraForms.WalkForm);
        window.stat.actionEnd();
    }
    else
    {
        window.stat.actionError( "No entries found matching \"{0}.\"".format ( window.options["query"] ) );
    }
}

function drawMap ( httpData )
{
    var addressNames;
    window.options = httpData.parameters;
    clearMap();

    //Loop through the people. add them to the list. This also creates a list of unique addresses.
    for (var i = 0; i < httpData.people.length; i++)
    {
        new Person(httpData.people[i]);
    }

    //all of the new people create a list of unique addresses in data addresses. Here we get their names
    addressNames = Object.keys(window.data.addresses);

    //Now loop through our links array and add those (
    for ( i = 0; i < httpData.links.length; i++ )
    {
        //note that parent, child here are IDs/Pointers
        window.data.links.push ( new AncestryLink ( httpData.links[i].parent, httpData.links[i].child ) );
    }

    window.stat.info ( "Ancestry parsed for {0}. {1} people retrieved. {2} links retrieved. {3} distinct addresses retrieved.".format ( httpData.people[0].name,  Object.keys(window.data.people).length, httpData.links.length, addressNames.length ) );

    window.mapper.reset();
    //Plot each unique address on the map
    for ( i = 0; i < addressNames.length; i++)
    {
        //This really should be a function on the address object but I had a little trouble with that.
        window.mapper.map(window.data.addresses[addressNames[i]]);
    }

    //Addresses are being mapped. Take our form away.
    showForm(MigraForms.View);

}

function showMigrations ( )
{
    var earliestDate = 3000;
    var latestDate = -3000;
    var keys = Object.keys(window.data.people);

    //The idea with this function is that we will progress through the people in our people
    for ( var i = 0; i < keys.length ; i++ )
    {
        key = keys[i];
        if ( window.data.people[key].date != null ) {
            if ( window.data.people[key].date < earliestDate ) earliestDate = window.data.people[key].date;
            if ( window.data.people[key].date > latestDate ) latestDate = window.data.people[key].date;
        }
    }

    showAllOverlays ( false );
    showMigrationMarkers ( earliestDate, latestDate );
}

function showAllOverlays(toggle)
{
    if ( ! toggle ) {
        window.clusterer.clearMarkers();
        window.spiderifier.clearMarkers();
    }

    for ( var i = 0; i < window.overlays.markers.length; i ++ )
    {
        window.overlays.markers[i].setVisible(toggle);
    }

    for ( var i = 0; i < window.overlays.polylines.length; i ++ )
    {
        window.overlays.polylines[i].setVisible(toggle);
    }

    if ( toggle )
    {
        window.clusterer.addMarkers ( window.overlays.markers );
        for ( var i = 0; i < window.overlays.markers.length; i ++ )
        {
            window.spiderifier.addMarker ( window.overlays.markers[i] );
        }
    }
}

function showMigrationMarkers ( startRange, endRange )
{
    var peopleKeys = Object.keys(window.data.people);
    var p;

    if ( startRange >= endRange )
    {
        showAllOverlays(true);
        return;
    }

    window.stat.info ( startRange + " - " + ( startRange + 30 ) );

    for ( i = 0; i < peopleKeys.length; i++ )
    {
        p = window.data.people[peopleKeys[i]];
        if ( p.marker )
        {
            b = ( p.date >= startRange && p.date < ( startRange + 30 ) );
            if ( p.date === undefined || p.date == null ) b = false;

            if ( b ) p.marker.setMap(window.map);
            p.marker.setVisible ( b );
        }
    }

    setTimeout ( function() { showMigrationMarkers ( startRange + 15, endRange ); }, 1000 );
}

function getRelationshipDesc ( person )
{
    var rel = ( person.generation == 0 ? "self" : ( person.sex == "M" ? "father" : "mother" ) );
    if ( person.generation > 1 ) rel = "grand" + rel;
    if ( person.generation > 2 ) rel = "great-" + rel;
    if ( person.generation > 3 )
    {
        var s=["th","st","nd","rd"],
        g=person.generation-2,
        v=g%100;
        rel = "" + ( g+(s[(v-20)%10]||s[v]||s[0]) ) + " " + rel;
    }
    return rel;
}

function xinspect(o,i){
    if(typeof i=='undefined')i='';
    if(i.length>50)return '[MAX ITERATIONS]';
    var r=[];
    for(var p in o){
        var t=typeof o[p];
        r.push(i+'"'+p+'" ('+t+') => '+(t=='object' ? 'object:'+xinspect(o[p],i+'  ') : o[p]+''));
    }
    return r.join(i+'\n');
}

google.maps.event.addDomListener(window, 'load', initialize);
