"""
Define report template here
"""

REPORT_TEMPLATE = r"""
<!-- This template prepare for a email report with 4+ tables, No JavaScript -->
<!-- <?xml version="1.0" encoding="UTF-8"?> -->
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
    <title>%(Title)s</title>
    <meta name="generator" content="%(Generator)s">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <style type="text/css" media="screen">
        body {
            font-family: verdana, arial, helvetica, sans-serif;
            font-size: 80%%;
        }

        table {
            font-size: 100%%;
        }

        /* -- heading ---------------------------------------------------------------------- */
        h1 {
            font-size: 16pt;
        }
        
        .h_green {
            color: #6c6;
        }
        
        .h_red {
            color: #FF0000;
        }

        .heading {
            margin-top: 0ex;
            margin-bottom: 1ex;
        }

        .heading .attribute {
            margin-top: 1ex;
            margin-bottom: 0;
        }

        .heading .description {
            margin-top: 4ex;
            margin-bottom: 6ex;
        }

        /* -- css div popup ------------------------------------------------------------------------ */
        a.popup_link:hover {
            color: red;
        }

        .popup_window {
            display: none;
            position: relative;
            left: 0px;
            top: 0px;
            /*border: solid #627173 1px; */
            padding: 10px;
            background-color: #E6E6D6;
            font-family: "Lucida Console", "Courier New", Courier, monospace;
            text-align: left;
            font-size: 8pt;
            width: 500px;
        }

        /* -- report ------------------------------------------------------------------------ */
        #show_detail_line {
            margin-top: 3ex;
            margin-bottom: 1ex;
        }

        #env_table {
            width: 80%%;
            border-collapse: collapse;
            border: 1px solid #777;
        }

        #node_table {
            width: 80%%;
            border-collapse: collapse;
            border: 1px solid #777;
        }

        #summary_table {
            width: 80%%;
            border-collapse: collapse;
            border: 1px solid #777;
        }

        #result_table {
            width: 80%%;
            border-collapse: collapse;
            border: 1px solid #777;
        }

        #header_row {
            font-weight: bold;
            color: white;
            background-color: #777;
        }

        #env_table td {
            border: 1px solid #777;
            padding: 2px;
        }

        #node_table td {
            border: 1px solid #777;
            padding: 2px;
        }

        #summary_table td {
            border: 1px solid #777;
            padding: 2px;
        }

        #result_table td {
            border: 1px solid #777;
            padding: 2px;
        }

        #summary_row {
            font-weight: bold;
        }

        #total_row {
            font-weight: bold;
        }

        .passClass {
            background-color: #6c6;
        }

        .failClass {
            background-color: #c60;
        }

        .errorClass {
            background-color: #c00;
        }

        .passCase {
            color: #6c6;
        }

        .failCase {
            color: #FF0000;
            font-weight: bold;
        }

        .errorCase {
            color: #900000;
            font-weight: bold;
        }
        
        .skipCase {
            color: #F0A20D;
            font-weight: bold;
        }

        .hiddenRow {
            display: none;
        }

        .testcase {
            margin-left: 2em;
        }

        /* -- ending ---------------------------------------------------------------------- */
    </style>
</head>

<body>
    <!-- Title -->
    <div class='heading'>
        <h1 class=%(TitleColor)s> %(Title)s </h1>
    </div>

    <!-- Test Env Information: -->
    <b> <span lang="EN-US" style="font-size:14.0pt">Environment:</span> </b>
    <table id='env_table' class="table table-condensed table-bordered table-hover">
        <!-- test ENV Description list -->
        %(Environment)s
    </table>
    </br>

    <!-- Test Nodes Information: -->
    <b> <span lang="EN-US" style="font-size:14.0pt">Nodes:</span> </b>
    <table id='node_table' class="table table-condensed table-bordered table-hover">
        <colgroup>
            <col align='left' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
        </colgroup>
        <tr id='env_table_header' class="text-center success" style="font-weight: bold;font-size: 14px;">
            <td align='center'>NodeName</td>
            <td align='center'>STATUS</td>
            <td align='center'>IP</td>
            <td align='center'>Roles</td>
            <td align='center'>User</td>
            <td align='center'>Password</td>
            <td align='center'>OS</td>
        </tr>
        <!-- test nodes list -->
        %(Nodes)s
    </table>
    </br>

    <!-- summary_table -->
    <b> <span lang="EN-US" style="font-size:14.0pt">Summary:</span> </b>
    <table id='summary_table' class="table table-condensed table-bordered table-hover">
        <colgroup>
            <col align='left' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
        </colgroup>
        <tr id='summary_table_header' class="text-center success" style="font-weight: bold;font-size: 14px;">
            <td>Total</td>
            <td>Pass</td>
            <td>Fail</td>
            <td>Error</td>
            <td>Skip</td>
            <td>Cancel</td>
            <td>Passing Rate</td>
        </tr>
        <!-- summary_row -->
        <tr id='result_tabl' class="text-center success">
            <td>%(Total)s</td>
            <td>%(Pass)s</td>
            <td>%(Fail)s</td>
            <td>%(Error)s</td>
            <td>%(Skip)s</td>
            <td>%(Cancel)s</td>
            <td>%(Passrate)s</td>
        </tr>
    </table>
    </br>

    <!-- case_results_table -->
    <b> <span lang="EN-US" style="font-size:14.0pt">Results:</span> </b>
    <table id='result_table' class="table table-condensed table-bordered table-hover">
        <colgroup>
            <col align='left' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
        </colgroup>
        <tr id='case_table_header' class="text-center success" style="font-weight: bold;font-size: 14px;">
            <td align='center'>Test Group/Case</td>
            <td align='center'>Status</td>
            <td align='center'>Elapsed Time</td>
            <td align='center'>Loop</td>
        </tr>
        <!-- test case list -->
        %(Results)s
    </table>
</body>

</html>
"""