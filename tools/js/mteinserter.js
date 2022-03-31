/**
 * MTE_Inserter
 */
var id = 1;
var idT = 1;
var idE = 1;

var ids = {"ev_id":0, "mpd_id":[]};

var miffeControl = {
	"sv_validtime": 0
};

var emsg_v0 = {
	"sv_validtime": 0,
	"scheme_id_uri": "emsg_v0",
	"value": "v0test",
	"timescale": 90000,
	"presentation_time_delta": 0,
	"event_duration": 0,
	"id": 0,
	"message_data": [0xff,0x80]
};
var emsg_v1 = {
	"sv_validtime": 0,
	"timescale": 90000,
	"presentation_time": 0,
	"event_duration": 0,
	"id": 0,
	"scheme_id_uri": "emsg_v1",
	"value": "v1test",
	"message_data": [0xff,0x80]
};

var mte_ins_method = {
	"target": "",
	"method": (-1),
	"b_interval": (-1),
	"b_duration": (-1),
	"c_duration": (-1)
}

var mte_emsg = {
	"scheme_id_uri": "",
	"value": "",
	"timescale": "",

	"ev_version": "",
	"ev_flags": "",
	"ev_presentation_time": "",
	"ev_duration": "",
	"ev_id": "",
	"ev_message_data": ""
};
var mte_mpd = {
	"scheme_id_uri": "",
	"value": "",
	"timescale": "",
	"href": "",
	"actuate": "",
	"event": []
};

//
// get_radio_value
//
function get_radio_value( name ) {
	var radio_value = "";
	var elements = document.getElementsByName( name );
	for ( var i=0; i<elements.length; i++ ) {
		if ( elements[i].checked ) {
			radio_value = elements[i].value ;
			break ;
		}
	}
	return radio_value;
}

//
// incrementID
//
function incrementID( msg ) {
	var retmsg = msg;
	if( msg["emsg"]["ev_id"] ) {
		retmsg["emsg"]["ev_id"] = ids["ev_id"];
		ids["ev_id"] = ids["ev_id"] + 1;
		document.getElementById("emsg_ev_id").value = ids["ev_id"];
	}

console.log

	if( msg["emsg"]["event"] ) {
		for( var i=0; i<msg["emsg"]["event"].length; i++ ) {
			retmsg["emsg"]["event"][i]["ev_id"] = ids["mpd_id"][i];
			ids["mpd_id"][i] = ids["mpd_id"][i] + 1;
			document.getElementById("mpd_ev" + (i+1) + "_id").value = ids["mpd_id"][i];
		}
	}

	return retmsg;
}

//
// convertBinary
//
function convertBinary( textdata ) {
	var b_data = new Array( textdata.length );
	for( var i=0; i<textdata.length; i++ ) {
		b_data[i] = textdata.charCodeAt(i);
	}
	return b_data;
}

//
// postAPI_emsg
//
function postAPI_emsg( msg ) {
	if( msg != null ) {
		var xhr = new XMLHttpRequest();	
		xhr.open("POST", '/mte', true);
		xhr.setRequestHeader("Content-Type", "application/json");
		xhr.onreadystatechange = function() {
			if (this.readyState === XMLHttpRequest.DONE && this.status === 200) {
			}
		}

		xhr.send( JSON.stringify(msg) );
	}
}

//
// postMTE
//
var postTimer;
var endTime;
function postMTE( msg ) {
	if( mte_ins_method["method"] == "A" ) {
		postAPI_emsg(incrementID(msg));
	}
	else if( mte_ins_method["method"] == "C" ) {
		postAPI_emsg(incrementID(msg));
	}
	else if( mte_ins_method["method"] == "B" ) {
		var interval = Number(mte_ins_method["b_interval"]);
		var duration = Number(mte_ins_method["b_duration"]);

console.log( interval + " " + duration );

		postAPI_emsg(incrementID(msg));
		if( interval <= duration ) {
			endTime = Date.now() + duration;
console.log( endTime );
			postTimer = setInterval( function(msg) {
				if( Date.now() <= endTime ) {
console.log( endTime - Date.now() );
					var amsg = incrementID(msg);
console.log( amsg );
					postAPI_emsg( amsg );
				}
				else {
					clearInterval(postTimer);
				}
			}, interval , msg);
		}
	}
}

//
// emsg_insert
//
function emsg_insert() {
	mte_ins_method["target"] = "emsg";
	mte_ins_method["method"] = get_radio_value("emsg_method");
	mte_ins_method["b_interval"] = document.getElementById("emsg_b_interval").value;
	mte_ins_method["b_duration"] = document.getElementById("emsg_b_duration").value;
	mte_ins_method["c_duration"] = document.getElementById("emsg_c_duration").value;

	mte_emsg["scheme_id_uri"]        = document.getElementById("emsg_scheme_id_uri").value;
	mte_emsg["value"]                = document.getElementById("emsg_value").value;
	mte_emsg["timescale"]            = parseInt( document.getElementById("emsg_timescale").value, 10);
	mte_emsg["ev_version"]           = parseInt( document.getElementById("emsg_ev_version").value, 10);
	mte_emsg["ev_flags"]             = parseInt( document.getElementById("emsg_ev_flags").value, 10);
	mte_emsg["ev_presentation_time"] = parseInt( document.getElementById("emsg_ev_presentation_time").value, 10);
	mte_emsg["ev_duration"]          = parseInt( document.getElementById("emsg_ev_duration").value, 10);
	mte_emsg["ev_id"]                = parseInt( document.getElementById("emsg_ev_id").value, 10 );
	mte_emsg["ev_message_data"]      = convertBinary( document.getElementById("emsg_ev_message_data").value );

	if( mte_ins_method["method"] == "B" ) {
		if( (mte_ins_method["b_interval"] == "") || (mte_ins_method["b_duration"] == "") ) {
			alert( "連続挿入間隔/期間を指定して下さい。" );
			return ;
		}
	}

	else if( mte_ins_method["method"] == "C" ) {
		if( mte_ins_method["c_duration"] == "" ) {
			alert( "セグメント挿入期間を指定して下さい。" );
			return ;
		}
	}

	ids["ev_id"] = mte_emsg["ev_id"];

	var msg = {"control":mte_ins_method, "emsg":mte_emsg};

	console.log(msg);
	postMTE(msg);
}

//
// mpd_insert
//
function mpd_insert() {
	mte_ins_method["target"] = "mpd";
	mte_ins_method["method"] = get_radio_value("mpd_method");
	mte_ins_method["b_interval"] = document.getElementById("mpd_b_interval").value;
	mte_ins_method["b_duration"] = document.getElementById("mpd_b_duration").value;
	mte_ins_method["c_duration"] = document.getElementById("mpd_c_duration").value;

	mte_mpd["scheme_id_uri"] = document.getElementById("mpd_scheme_id_uri").value;
	mte_mpd["value"]         = document.getElementById("mpd_value").value;
	mte_mpd["timescale"]     = document.getElementById("mpd_timescale").value;
	mte_mpd["href"]          = document.getElementById("mpd_href").value;
	mte_mpd["actuate"]       = document.getElementById("mpd_actuate").value;

	var event1 = {
		"ev_presentation_time": parseInt(document.getElementById("mpd_ev1_presentation_time").value, 10),
		"ev_duration":          parseInt(document.getElementById("mpd_ev1_duration").value, 10),
		"ev_id":                parseInt(document.getElementById("mpd_ev1_id").value, 10),
		"ev_message_data":      document.getElementById("mpd_ev1_message_data").value
	};
	var event2 = {
		"ev_presentation_time": parseInt(document.getElementById("mpd_ev2_presentation_time").value, 10),
		"ev_duration":          parseInt(document.getElementById("mpd_ev2_duration").value, 10),
		"ev_id":                parseInt(document.getElementById("mpd_ev2_id").value, 10),
		"ev_message_data":      document.getElementById("mpd_ev2_message_data").value
	};
	var event3 = {
		"ev_presentation_time": parseInt(document.getElementById("mpd_ev3_presentation_time").value, 10),
		"ev_duration":          parseInt(document.getElementById("mpd_ev3_duration").value, 10),
		"ev_id":                parseInt(document.getElementById("mpd_ev3_id").value, 10),
		"ev_message_data":      document.getElementById("mpd_ev3_message_data").value
	};

	if( mte_ins_method["method"] == "B" ) {
		if( (mte_ins_method["b_interval"] == "") || (mte_ins_method["b_duration"] == "") ) {
			alert( "連続挿入間隔/期間を指定して下さい。" );
			return ;
		}
	}

	else if( mte_ins_method["method"] == "C" ) {
		if( mte_ins_method["c_duration"] == "" ) {
			alert( "セグメント挿入期間を指定して下さい。" );
			return ;
		}
	}

	mte_mpd["event"] = [];
	mte_mpd["event"].push( event1 );
	mte_mpd["event"].push( event2 );
	mte_mpd["event"].push( event3 );

	ids["mpd_id"][0] = mte_mpd["event"][0]["ev_id"];
	ids["mpd_id"][1] = mte_mpd["event"][1]["ev_id"];
	ids["mpd_id"][2] = mte_mpd["event"][2]["ev_id"];

	var msg = {"control":mte_ins_method, "emsg":mte_mpd};

	console.log(msg);
	postMTE(msg);
}
