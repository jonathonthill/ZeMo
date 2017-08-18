#!/usr/bin/python3.4

import yaml
import cgi
import cgitb

cgitb.enable()

print("Content-Type: text/html\n\n")

cfg_file = open("/home/pi/FishCode/Configure.yaml")
cfg = yaml.load(cfg_file)

# Getter for values
def getShadowValues(range, sensor):
    try:
        return cfg[range][sensor]
    except Exception as e:
        return "null"

# Editor for values
def changeShadowValues(range, sensor, currVal):
    cfg[range][sensor] = currVal
    cfg["needUpdate"]["update"] = "yes"
    with open("/home/pi/FishCode/Configure.yaml", "w") as f:
        yaml.dump(cfg, f)

# Grabs form values and updates the file with the new values
def grabFormValues(range, sensor, sensorRange):
    if form.getvalue(sensorRange) is None:
        currSensor = getShadowValues(range, sensor)
    else:
        currSensor = form.getvalue(sensorRange)
        changeShadowValues(range, sensor, currSensor)
    return currSensor

# Sets correct placeholder values
form = cgi.FieldStorage()
lowpH = grabFormValues("lowRange", "PH", "pHLower")
upperpH = grabFormValues("highRange", "PH", "pHUpper")
lowTemp = grabFormValues("lowRange", "T", "tempLower")
upperTemp = grabFormValues("highRange", "T", "tempUpper")
lowCond = grabFormValues("lowRange", "EC", "condLower")
upperCond = grabFormValues("highRange", "EC", "condUpper")
lowDO = grabFormValues("lowRange", "DO", "dOLower")
upperDO = grabFormValues("highRange", "DO", "dOUpper")
readsPerDay = grabFormValues("readsPerDay", "reads", "readsPerDay")
daysToKeep = grabFormValues("daysStored", "days", "daysToKeep")

text_file = open("/home/pi/FishCode/EmailList.txt", "r")

# Add email
if ("submit2" in form or "<Return>" in form):
        if form.getvalue('emailToAdd') != None:
            emailToAdd = form.getvalue('emailToAdd')
            newEmailList = []
            emailFile = open("/home/pi/FishCode/EmailList.txt", "r")
            inList = False
            with open("/home/pi/FishCode/EmailList.txt", "r") as f:
                for line in f:
                    cleanedLine = line.strip()
                    if cleanedLine:
                        if cleanedLine == emailToAdd:
                            inList = True
                        else:
                            newEmailList.append(cleanedLine)
            if(inList == False):
                emailFile = open("/home/pi/FishCode/EmailList.txt", "a")
                emailFile.write("\n" + emailToAdd)
                newEmailList.append(emailToAdd)
            emailFile.close()
            cfg["needUpdate"]["update"] = "yes"
            with open("/home/pi/FishCode/Configure.yaml", "w") as f:
                yaml.dump(cfg, f)
else:
    # Remove email
        emailToRemove = ""
        newEmailList = []
        emailFile = open("/home/pi/FishCode/EmailList.txt", "r")
        inList = False
        with open("/home/pi/FishCode/EmailList.txt", "r") as f:
            for line in f:
                cleanedLine = line.strip()
                if cleanedLine:
                    emailToRemove = "remove" + cleanedLine
                    if ("Remove") == form.getvalue(emailToRemove):
                        inList = True
                    else:
                        newEmailList.append(cleanedLine)
        emailFile.close()
        if(inList == True):
            emailFile = open("/home/pi/FishCode/EmailList.txt","w")
            for emailList in newEmailList:
                emailFile.write("\n" + emailList)
        emailFile.close()
        cfg["needUpdate"]["update"] = "yes"
        with open("/home/pi/FishCode/Configure.yaml", "w") as f:
            yaml.dump(cfg, f)

# Adds the emails to the webpage
with open("/home/pi/FishCode/EmailList.txt", "r") as f:
    emailTable = ""
    for line in f:
        cleanedLine = line.strip()
        if cleanedLine:
            emailTable = emailTable + """
                    <tr>
                        <td class="id" style="display:none;">1</td>
                        <td class="email">%s</td>
                        <td class="remove"><input type="submit" name="remove%s" id="Remove" value="Remove" onclick="this.form.submitted=&#34;&#34;">
                    </tr>
""" % (cleanedLine, cleanedLine)

text_file.close()

# Prints the webpage
printString = """
<!DOCTYPE html>
<html>
<head>
<script language="javascript">
// Python requires double brackets to read javascript
function ValidateEmail(inputEmail)
{{
    if(document.UpdateAll.condLower.value != "")
        {{
            low=document.UpdateAll.condLower.value;
        }}
        else
        {{
            low=document.UpdateAll.condLower.id;
        }}
        if(document.UpdateAll.condUpper.value != "")
        {{
            high=document.UpdateAll.condUpper.value;
        }}
        else
        {{
            high=document.UpdateAll.condUpper.id;
        }}
        if(isNaN(low) || isNaN(high))
        {{
            alert("You must use numeric values in your ranges.");
            return false;    
        }}
        else
        {{
            if(parseInt(low) >= parseInt(high))
            {{
                alert("Your lower ranges must be less than your higher ranges.");
                return false;
            }}
            if(parseInt(low) < 0 || parseInt(high) < 0)
            {{
                alert("Your ranges must be positive values.");
                return false;
            }}
        }}
        if(document.UpdateAll.dOLower.value != "")
        {{
            low=document.UpdateAll.dOLower.value;
        }}
        else
        {{
            low=document.UpdateAll.dOLower.id;
        }}
        if(document.UpdateAll.dOUpper.value != "")
        {{
            high=document.UpdateAll.dOUpper.value;
        }}
        else
        {{
            high=document.UpdateAll.dOUpper.id;
        }}
        if(isNaN(low) || isNaN(high))
        {{
            alert("You must use numeric values in your ranges.");
            return false;    
        }}
        else
        {{
            if(parseInt(low) >= parseInt(high))
            {{
                alert("Your lower ranges must be less than your higher ranges.");
                return false;
            }}
            if(parseInt(low) < 0 || parseInt(high) < 0)
            {{
                alert("Your ranges must be positive values.");
                return false;
            }}
        }}
        if(document.UpdateAll.tempLower.value != "")
        {{
            low=document.UpdateAll.tempLower.value;
        }}
        else
        {{
            low=document.UpdateAll.tempLower.id;
        }}
        if(document.UpdateAll.tempUpper.value != "")
        {{
            high=document.UpdateAll.tempUpper.value;
        }}
        else
        {{
            high=document.UpdateAll.tempUpper.id;
        }}
        if(isNaN(low) || isNaN(high))
        {{
            alert("You must use numeric values in your ranges.");
            return false;    
        }}
        else
        {{
            if(parseInt(low) >= parseInt(high))
            {{
                alert("Your lower ranges must be less than your higher ranges.");
                return false;
            }}
            if(parseInt(low) < 0 || parseInt(high) < 0)
            {{
                alert("Your ranges must be positive values.");
                return false;
            }}
        }}
        if(document.UpdateAll.pHLower.value != "")
        {{
            low=document.UpdateAll.pHLower.value;
        }}
        else
        {{
            low=document.UpdateAll.pHLower.id;
        }}
        if(document.UpdateAll.pHUpper.value != "")
        {{
            high=document.UpdateAll.pHUpper.value;
        }}
        else
        {{
            high=document.UpdateAll.pHUpper.id;
        }}
        if(isNaN(low) || isNaN(high))
        {{
            alert("You must use numeric values in your ranges.");
            return false;    
        }}
        else
        {{
            if(parseInt(low) >= parseInt(high))
            {{
                alert("Your lower ranges must be less than your higher ranges.");
                return false;
            }}
            if(parseInt(low) < 0 || parseInt(high) < 0)
            {{
                alert("Your ranges must be positive values.");
                return false;
            }}
        }}
var mailformat = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
if(inputEmail.value.match(mailformat))
{{
document.UpdateAll.emailToAdd.focus();
return true;
}}
else if(inputEmail.value != "")
{{
alert("You have entered an invalid email address!");
document.UpdateAll.emailToAdd.focus();
return false;
}}
}}
</script>
</head>
<body onload='document.UpdateAll.emailToAdd.focus()'>    
    <form name="UpdateAll" action="UpdateZeMo.py" method="post" onsubmit="return ValidateEmail(this.submitted);">
        <h2>Adjust Sensor Warning Range</h2>
        <table>
            <thead>
                <tr>
                    <th>Sensor</th>
                    <th>Lower Range</th>
                    <th>Upper Range</th>
                </tr>
            </thead>
            <tbody align=center>
                <tr>
                    <td>Conductivity: </td>
                    <td>
                        <input type="text" name="condLower" id="{9}" placeholder="{0}")
                    </td>
                    <td>
                        <input type="text" name="condUpper" id="{10}" placeholder="{1}">
                    </td>
                </tr>
                <tr>
                    <td>Dissolved Oxygen: </td>
                    <td>
                        <input type="text" name="dOLower" id="{11}" placeholder="{2}">
                    </td>
                    <td>
                        <input type="text" name="dOUpper" id="{12}" placeholder="{3}">
                    </td>
                </tr>
                <tr>
                    <td>Temperature: </td>
                    <td>
                        <input type="text" name="tempLower" id="{13}" placeholder="{4}">
                    </td>
                    <td>
                        <input type="text" name="tempUpper" id="{14}" placeholder="{5}">
                    </td>
                </tr>
                <tr>
                    <td>pH: </td>
                    <td>
                        <input type="text" name="pHLower" id="{15}" placeholder="{6}">
                    </td>
                    <td>
                        <input type="text" name="pHUpper" id="{16}" placeholder="{7}">
                    </td>
                </tr>
                <tr>
                    <td>Reads Per Day: </td>
                    <td>
                        <input type="text" name="readsPerDay" id="{17}" placeholder="{18}">
                    </td>
                </tr>
                <tr>
                    <td>Days to Keep: </td>
                    <td>
                        <input type="text" name="daysToKeep" id="{19}" placeholder="{20}">
                    </td>
                </tr>

        </table>
        <br>
        <input type="submit" name="submit2" value="Update Values" id="Range" onclick="this.form.submitted=emailToAdd">
        <br>
        <input type="submit" name="submit2" value="Add" id="Add" hidden="hidden" onclick="this.form.submitted=emailToAdd"/>
        <h2>Edit Email List</h2>
        <div id="contacts">
            <table>
                <tbody class="list">
                {8}
                </tbody>
            </table>
            <table>
                <td class="city">
                    <input type="text" name="emailToAdd" placeholder="example@gmail.com" />
                </td>
                <td class="add">
                    <input type="submit" name="submit2" value="Add" id="Add" onclick="this.form.submitted=emailToAdd">
                </td>
            </table>
    </form>
</body>
</html>
"""

print(printString.format(lowCond, upperCond, lowDO, upperDO, lowTemp, upperTemp, lowpH, upperpH, 
                         emailTable.format(), lowCond, upperCond, lowDO, upperDO, lowTemp, upperTemp, lowpH, upperpH, 
                         readsPerDay, readsPerDay, daysToKeep, daysToKeep))

# TODO clean up code, so repetitive stuff is recycled (remove recurring code) - javascript section
# TODOlow can't submit other values or remove emails with a bad email address in 'add' text block