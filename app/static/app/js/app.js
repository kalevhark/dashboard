function getDirection(angle) {
  var directions = ['N', 'NW', 'W', 'SW', 'S', 'SE', 'E', 'NE'];
  return directions[Math.round(((angle %= 360) < 0 ? angle + 360 : angle) / 45) % 8];
}


function update_xaxis_categories(url, chart) {
  // Küsime x-telje andmed ja täiendame graafikut
  $.ajax({
    url: url,
    dataType: 'json',
    timeout: 300000,
	beforeSend: function() {
      // $("#loaderDiv3").show();
    },
    success: function (data) {
      // console.log(data);
      chart.xAxis[0].setCategories(data);
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  console.log(XMLHttpRequest, textstatus, errorThrown);
    },
	complete: function () {
	  // $("#loaderDiv3").hide();
	}
  });
};

function update_ilmateenistus_now_data(url, chart) {
  // Küsime ilmateenistuse andmed ja täiendame graafikut
  $.ajax({
    url: url,
    dataType: 'json',
    timeout: 300000,
	beforeSend: function() {
      // $("#loaderDiv3").show();
    },
    success: function (data) {
      console.log(data);
      let elAirtemperature = $('#ilmateenistus_airtemperature')
      elAirtemperature.text(data.airtemperature);
      elAirtemperature.addClass('color-' + data.airtemperature_colorclass);

      let elRelativehumidity = $('#ilmateenistus_relativehumidity')
      elRelativehumidity.text(data.relativehumidity);
      elRelativehumidity.addClass('color-' + data.relativehumidity_colorclass);

      let elIlmateenistusWindSpeed = $('#ilmateenistus_windspeed');
      elIlmateenistusWindSpeed.text(data.windspeed);

      let elIlmateenistusWindSpeedMax = $('#ilmateenistus_windspeedmax');
      elIlmateenistusWindSpeedMax.text(data.windspeedmax);

      if ( data.phenomenon !== null ) {
        let elIlmateenistusPhenomen = $('#ilmateenistusPhenomen');
        elIlmateenistusPhenomen.className = "";
        elIlmateenistusPhenomen.className = "weather-icon " + data.phenomenon.toLowerCase();
      }

      let elIlmateenistusWinddirection = $('#ilmateenistus_winddirection');
      elIlmateenistusWinddirection.text(getDirection(data.winddirection));

      let windIcon = document.getElementById("ilmateenistusWindOrientation");
      let windDirection = data.winddirection;
      windIcon.setAttribute("alt", windDirection);
      windIcon.setAttribute("title", windDirection);
      windIcon.className = windIcon.className.replace( /(?:^|\s)(direction-).*[0-9]$/g , '');
      windIcon.className += " direction-" + windDirection.toString().slice(0,-1) + "0";
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  console.log(XMLHttpRequest, textstatus, errorThrown);
    },
	complete: function () {
	  // $("#loaderDiv3").hide();
	}
  });
};

function update_yrno_next12h_data(url, chart) {
  // Küsime yrno andmed ja täiendame graafikut
  $.ajax({
    url: url,
    dataType: 'json',
    timeout: 300000,
	beforeSend: function() {
      // $("#loaderDiv3").show();
    },
    success: function (data) {
      console.log(data);
      const arr_12h_nulls = new Array(12).fill(null);
      chart.get('next_12hour_outdoor_temp').update({data: arr_12h_nulls.concat(data.next_12hour_outdoor_temp)});
      chart.get('next_12hour_outdoor_prec_err').update({data: arr_12h_nulls.concat(data.next_12hour_outdoor_prec_err)});
      chart.get('next_12hour_outdoor_prec_min').update({data: arr_12h_nulls.concat(data.next_12hour_outdoor_prec_min)});
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  console.log(XMLHttpRequest, textstatus, errorThrown);
    },
	complete: function () {
	  // $("#loaderDiv3").hide();
	}
  });
};

function update_aquarea_serv_data(url, chart) {
  // Küsime aquarea andmed ja täiendame graafikut
  $.ajax({
    url: url,
    dataType: 'json',
    timeout: 300000,
	  beforeSend: function() {
      // $("#loaderDiv3").show();
      $("#img31").addClass('spinner');
    },
    success: function (data) {
      console.log(data);
      // const arr_12h_nulls = new Array(12).fill(null);
      // chart.series[0].update({data: data.act_outd_temp}); // 5 minuti kaupa on liiga sakiline
      // chart.get('tot_gen').update({data: data.tot_gen});
      chart.get('last_12hour_consum_heat').update({data: data.heat_con});
      chart.get('last_12hour_consum_tank').update({data: data.tank_con});
      chart.get('last_12hour_tot_gen_plus').update({data: data.tot_gen_plus});

      let elZone1Status_temp = $('#z1_water_temp');
      elZone1Status_temp.text(data.status.z1_water_temp);
      let elZone1Status_temp_target = $('#zone1Status_temp_target');
      elZone1Status_temp_target.text(data.status.z1_water_temp_target);

      let elZone2Status_temp = $('#z2_water_temp');
      elZone2Status_temp.text(data.status.z2_water_temp);
      let elZone2Status_temp_target = $('#zone2Status_temp_target');
      elZone2Status_temp_target.text(data.status.z2_water_temp_target);

      let elOlet_water_temp = $('#olet_water_temp');
      elOlet_water_temp.text(data.status.olet_water_temp.toFixed(1));
      let elIlet_water_temp = $('#ilet_water_temp');
      elIlet_water_temp.text(data.status.ilet_water_temp.toFixed(1));
      $("#img24").removeClass('spinner');

      let elTankStatus_temp_now = $('#tankStatus_temp_now');
      elTankStatus_temp_now.text(data.status.tank_temp);
      let elTankStatus_temp_target = $('#tankStatus_temp_target');
      elTankStatus_temp_target.text(data.status.tank_temp_target);

      let elAct_outd_temp = $('#act_outd_temp')
      elAct_outd_temp.text(data.status.act_outd_temp);
      if (data.status.act_outd_temp > 0) {
        elAct_outd_temp.addClass('color-red');
      } else {
        elAct_outd_temp.addClass('color-blue');
      }
      $("#img31").removeClass('spinner');
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  console.log(XMLHttpRequest, textstatus, errorThrown);
    },
	  complete: function () {
	    // $("#loaderDiv3").hide();
	  }
  });
};

function update_aquarea_smrt_data_day(url, chart) {
  // Küsime:
  // - aquarea tänased ja eilsed andmed
  // - hetketöörežiimi
  // - nädalagraafikus
  // Täiendame graafikut
  $.ajax({
    url: url,
    dataType: 'json',
    timeout: 300000,
	  beforeSend: function() {
      // $("#loaderDiv3").show();
      $("#img21").addClass('spinner');
      $("#img22").addClass('spinner');
      $("#img23").addClass('spinner');
      $("#img24").addClass('spinner');
    },
    success: function (data) {
      console.log(data);

      chart.get('last_12hour_outdoor_temp').update({data: data.last_12hour_outdoor_temp});

      // current date
      let d = new Date();
      const ye = new Intl.DateTimeFormat('en', { year: 'numeric' }).format(d);
      const mo = new Intl.DateTimeFormat('en', { month: '2-digit' }).format(d);
      const da = new Intl.DateTimeFormat('en', { day: '2-digit' }).format(d);
      const ho = new Intl.DateTimeFormat('en', { hour: '2-digit', hour12: false }).format(d);
      const mi = new Intl.DateTimeFormat('en', { minute: 'numeric' }).format(d).padStart(2, '0');
      // dateString = `${da}.${mo}.${ye} ${ho}:${mi}`;
      dateString = `${ho % 24}:${mi}`;

      // console.log(data.status.status[0].zoneStatus[0].operationStatus);
      if (data.status.status[0].zoneStatus[0].operationStatus === 1) {
        $("#zone1Status_temp_target").show();
        $("#z1_water_temp").addClass('color-red');
      } else {
        $("#zone1Status_temp_target").hide();
      };
      $("#img21").removeClass('spinner');

      if (data.status.status[0].zoneStatus[1].operationStatus === 1) {
        $("#zone2Status_temp_target").show();
        $("#z2_water_temp").addClass('color-red');
      } else {
        $("#zone2Status_temp_target").hide();
      };
      $("#img22").removeClass('spinner');

      if (data.status.status[0].tankStatus[0].operationStatus === 1) {
        $("#tankStatus_temp_target").show();
        $("#tankStatus_temp_now").addClass('color-red');
      } else {
        $("#tankStatus_temp_target").hide();
      };
      $("#img23").removeClass('spinner');

      $('.text-day').css("visibility", "visible");

      $('#aquarea_consum_date').text(dateString);

      $('#t2na_tot').text((data.t2na_heat+data.t2na_tank).toFixed(1));
      $('#t2na_heat').text(data.t2na_heat.toFixed(1));
      $('#t2na_tank').text(data.t2na_tank.toFixed(1));

      $('#eile_tot').text((data.eile_heat+data.eile_tank).toFixed(1));
      $('#eile_heat').text(data.eile_heat.toFixed(1));
      $('#eile_tank').text(data.eile_tank.toFixed(1));
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  console.log(XMLHttpRequest, textstatus, errorThrown);
    },
	  complete: function () {
	    // $("#loaderDiv3").hide();
	  }
  });
};

function update_aquarea_smrt_data_month(url, chart) {
  // Küsime:
  // - aquarea selle ja eelmise kuu andmed
  $.ajax({
    url: url,
    dataType: 'json',
    timeout: 300000,
	  beforeSend: function() {
      // $("#loaderDiv3").show();
      $('.spinner-month').css( {"visibility": "visible"} );
    },
    success: function (data) {
      console.log(data);
      if ($.isEmptyObject(data) === false) {
        $('.text-month').css("visibility", "visible");

        $('#kuu_tot').text((data.kuu_heat + data.kuu_tank).toFixed(1));
        $('#kuu_heat').text(data.kuu_heat.toFixed(1));
        $('#kuu_tank').text(data.kuu_tank.toFixed(1));

        $('#kuu_eelmine_tot').text((data.kuu_eelmine_heat + data.kuu_eelmine_tank).toFixed(1));
        $('#kuu_eelmine_heat').text(data.kuu_eelmine_heat.toFixed(1));
        $('#kuu_eelmine_tank').text(data.kuu_eelmine_tank.toFixed(1));

        $('#kuu_aasta_tagasi_tot').text((data.kuu_aasta_tagasi_heat + data.kuu_aasta_tagasi_tank).toFixed(1));
        $('#kuu_aasta_tagasi_heat').text(data.kuu_aasta_tagasi_heat.toFixed(1));
        $('#kuu_aasta_tagasi_tank').text(data.kuu_aasta_tagasi_tank.toFixed(1));
      } else {
        $('.text-month').css( {"visibility": "visible", "color": "lightgray"} );
      }
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	    console.log(XMLHttpRequest, textstatus, errorThrown);
    },
	  complete: function () {
	    // $("#loaderDiv3").hide();
      $('.spinner-month').css( {"visibility": "collapse"} );
	  }
  });
}

function update_aquarea_smrt_data_year(url, chart) {
  // Küsime:
  // - aquarea selle ja eelmise perioodi andmed
  $.ajax({
    url: url,
    dataType: 'json',
    timeout: 300000,
	  beforeSend: function() {
      // $("#loaderDiv3").show();
      $('.spinner-year').css( {"visibility": "visible"} );
    },
    success: function (data) {
      console.log(data);
      if ($.isEmptyObject(data) === false) {
        $('.text-year').css( "visibility", "visible" );

        $('#jooksva_perioodi_tot').text((data.jooksva_perioodi_heat + data.jooksva_perioodi_tank).toFixed(1));
        $('#jooksva_perioodi_heat').text(data.jooksva_perioodi_heat.toFixed(1));
        $('#jooksva_perioodi_tank').text(data.jooksva_perioodi_tank.toFixed(1));

        $('#eelmise_perioodi_tot').text((data.eelmise_perioodi_heat + data.eelmise_perioodi_tank).toFixed(1));
        $('#eelmise_perioodi_heat').text(data.eelmise_perioodi_heat.toFixed(1));
        $('#eelmise_perioodi_tank').text(data.eelmise_perioodi_tank.toFixed(1));
      } else {
        $('.text-year').css( {"visibility": "visible", "color": "lightgray"} );
      }
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  console.log(XMLHttpRequest, textstatus, errorThrown);
    },
	complete: function () {
	  // $("#loaderDiv3").hide();
    $('.spinner-year').css( {"visibility": "collapse"} );
	}
  });
}

function update_ezr_data(url) {
  // Küsime ezr andmed ja täiendame graafikut
  $.ajax({
    url: url,
    dataType: 'json',
    timeout: 300000,
    retryCount: 1,
    retryLimit: 5,
	beforeSend: function() {
      // $("#loaderDiv3").show();
      $("#img11").addClass('spinner');
      $("#img12").addClass('spinner');
      $("#img13").addClass('spinner');
      $("#img14").addClass('spinner');
    },
    success: function (data) {
      console.log(data);
      let elHeatArea1_t_actual = $('#HeatArea1_t_actual');
      elHeatArea1_t_actual.text(data.nr1.t_actual);
      if (data.nr1.actor === '1') {
        elHeatArea1_t_actual.addClass('color-red');
      }
      let elHeatArea1_t_target = $('#HeatArea1_t_target');
      elHeatArea1_t_target.text(data.nr1.t_target);
      let elHeatArea1_heatarea_name = $('#HeatArea1_heatarea_name')
      elHeatArea1_heatarea_name.text(data.nr1.heatarea_name);
      document.getElementById('HeatArea1_actor_percent').value = data.nr1.actor_percent;
      $("#img11").removeClass('spinner');

      let elHeatArea2_t_actual = $('#HeatArea2_t_actual');
      elHeatArea2_t_actual.text(data.nr2.t_actual);
      if (data.nr2.actor === '1') {
        elHeatArea2_t_actual.addClass('color-red');
      }
      let elHeatArea2_t_target = $('#HeatArea2_t_target');
      elHeatArea2_t_target.text(data.nr2.t_target);
      let elHeatArea2_heatarea_name = $('#HeatArea2_heatarea_name');
      elHeatArea2_heatarea_name.text(data.nr2.heatarea_name);
      document.getElementById('HeatArea2_actor_percent').value = data.nr2.actor_percent;
      $("#img12").removeClass('spinner');

      let elHeatArea3_t_actual = $('#HeatArea3_t_actual');
      elHeatArea3_t_actual.text(data.nr3.t_actual);
      if (data.nr3.actor === '1') {
        elHeatArea3_t_actual.addClass('color-red');
      }
      let elHeatArea3_t_target = $('#HeatArea3_t_target');
      elHeatArea3_t_target.text(data.nr3.t_target);
      let elHeatArea3_heatarea_name = $('#HeatArea3_heatarea_name');
      elHeatArea3_heatarea_name.text(data.nr3.heatarea_name);
      document.getElementById('HeatArea3_actor_percent').value = data.nr3.actor_percent;
      $("#img13").removeClass('spinner');

      let elHeatArea4_t_actual = $('#HeatArea4_t_actual');
      elHeatArea4_t_actual.text(data.nr4.t_actual);
      if (data.nr4.actor === '1') {
        elHeatArea4_t_actual.addClass('color-red');
      }
      let elHeatArea4_t_target = $('#HeatArea4_t_target');
      elHeatArea4_t_target.text(data.nr4.t_target);
      let elHeatArea4_heatarea_name = $('#HeatArea4_heatarea_name');
      elHeatArea4_heatarea_name.text(data.nr4.heatarea_name);
      document.getElementById('HeatArea4_actor_percent').value = data.nr4.actor_percent;
      $("#img14").removeClass('spinner');
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
      this.retryCount++;
      if (this.retryCount <= this.retryLimit) {
        //try again
        var ajaxObject = this;
        window.setTimeout(function(){
            $.ajax(ajaxObject);
        },5000);
      } else {
        //user comes here After trying in the if loop for 5 times, with each request having five seconds delay. I am not able to keep delay between each request
        console.log(XMLHttpRequest, textstatus, errorThrown);
      }
    },
	complete: function () {
	  // $("#loaderDiv3").hide();
	}
  });
}

function update_get_tuyaapi_data(url, chart) {
  // Küsime:
  // - aquarea selle ja eelmise perioodi andmed
  $.ajax({
    url: url,
    dataType: 'json',
    timeout: 300000,
	beforeSend: function() {
      // $("#loaderDiv3").show();
    },
    success: function (data) {
      console.log(data);
      if (data.dps['1']) {
        // console.log('ON');
        document.getElementById("img23a").style.visibility = "visible";
      } else {
        // console.log('OFF');
        document.getElementById("img23a").style.visibility = "hidden";
      }
      // $('#jooksva_perioodi_tot').text((data.jooksva_perioodi_heat+data.jooksva_perioodi_tank).toFixed(1));
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  console.log(XMLHttpRequest, textstatus, errorThrown);
    },
	complete: function () {
	  // $("#loaderDiv3").hide();
	}
  });
}