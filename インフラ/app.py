# coding: utf-8
from flask import Flask, request, Markup, render_template
import csv
import time
import json

app = Flask(__name__)

def auth(value):
	return value=="LWwgrDhtPnwjhYw3YB7E"

def para_check(req, arr):
	for r in req:
		if arr.args.get(r) == None:
			return (False, r)
	return (True, "")

@app.route("/")
def hello():
    return render_template('index.html')

@app.route("/inout/register", methods=["GET"])
def inout():
	if not auth(request.headers.get("auth")):
		return "Incorrect authorization code.", 401
	required = ["mac", "status"]
	optional = ["time"]
	t = para_check(required, request)
	if not t[0]:
		return "Missing parameter [{}]".format(t[1]), 430
	data = {}
	for i in required:
		data[i] = request.args.get(i)
	if not (data["status"]=="exit" or data["status"]=="enter"):
		return "Parameter [status] is wrong.", 431
	if request.args.get("time") == None:
		data["time"] = str(int(time.time()))
	else:
		data["time"] = request.args.get("time")

	with open("/var/www/flask/inout.csv", mode="a", encoding="utf-8") as f:
		f.write("\t".join(data.values())+"\n")

	return json.dumps({"mac": data["mac"]})

@app.route("/inout/view")
def inout_view():
	with open("/var/www/flask/inout.csv", mode="r", encoding="utf-8") as f:
		data = [i for i in csv.reader(f, delimiter="\t") if i[0]!=""]
	body = '<table>'
	for a,b,c in data:
		body+='<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(a,b,c)
	body+= '</table>'
	return body

#esp device
@app.route("/esp32/register", methods=["GET"])
def esp32_register():
	if not auth(request.headers.get("auth")):
		return "Incorrect authorization code.", 401
	required = ["mac"]
	optional = ["release"]
	t = para_check(required, request)
	if not t[0]:
		return "Missing parameter [{}]".format(t[1]), 430
	data = {}
	for i in required:
		data[i] = request.args.get(i)
	if request.args.get("release") == None:
		data["release"] = 0
	else:
		data["release"] = int(request.args.get("release"))
	if data["release"]==1:
		with open("/var/www/flask/mac.csv", mode="r", encoding="utf-8") as f:
			l = set([i[0] for i in csv.reader(f) if i[0]!=""])
		if data["mac"] not in l:
			return "mac [{}] doesn't exist.".format(data["mac"]), 432
		else:
			l.remove(data["mac"])
			with open("/var/www/flask/mac.csv", mode="w", encoding="utf-8") as f:
				f.write("\n".join(list(l)))
	else:
		with open("/var/www/flask/mac.csv", mode="r", encoding="utf-8") as f:
			l = set([i[0] for i in csv.reader(f) if i[0]!=""])
		if data["mac"] in l:
			return "[{}] is already registered.".format(data["mac"]), 431
		else:
			l.add(data["mac"])
			with open("/var/www/flask/mac.csv", mode="w", encoding="utf-8") as f:
				f.write("\n".join(list(l)))
	return esp32_list(j=True)

@app.route("/esp32/list", methods=["GET"])
def esp32_list(j=True):
	if not auth(request.headers.get("auth")):
		return "Incorrect authorization code.", 401
	with open("/var/www/flask/mac.csv", mode="r", encoding="utf-8") as f:
		l = [i[0] for i in csv.reader(f) if i[0]!=""]
	if j:
		return json.dumps({"mac": l})
	return "ERROR"

@app.route("/esp32/is_in", methods=["GET"])
def esp32_is_in():
	if not auth(request.headers.get("auth")):
		return "Incorrect authorization code.", 401
	required = ["mac"]
	t = para_check(required, request)
	if not t[0]:
		return "Missing parameter [{}]".format(t[1]), 430
	data = {}
	for i in required:
		data[i] = request.args.get(i)
	if data["mac"] in json.loads(esp32_list())["mac"]:
		boo = 1
	else:
		boo = 0
	return json.dumps({"is_in": boo})

@app.route("/rssi/register", methods=["GET"])
def rssi_register():
	if not auth(request.headers.get("auth")):
		return "Incorrect authorization code.", 401
	required = ["mac1","mac2","rssi"]
	t = para_check(required, request)
	if not t[0]:
		return "Missing parameter [{}]".format(t[1]), 430
	data = {}
	for i in required:
		data[i] = request.args.get(i)
	with open("/var/www/flask/rssi.csv", mode="r", encoding="utf-8") as f:
		l = {tuple(list(sorted(i[:2]))):i[2] for i in csv.reader(f, delimiter="\t")}
	l[tuple(list(sorted([data["mac1"],data["mac2"]])))] = data["rssi"]
	output = ""
	for m1,m2 in l:
		output+="{}\t{}\t{}\n".format(m1,m2,l[(m1,m2)])
	with open("/var/www/flask/rssi.csv", mode="w", encoding="utf-8") as f:
		f.write(output)
	return rssi_list()

@app.route("/rssi/list", methods=["GET"])
def rssi_list():
	if not auth(request.headers.get("auth")):
		return "Incorrect authorization code.", 401
	with open("/var/www/flask/rssi.csv", mode="r", encoding="utf-8") as f:
		l = {tuple(list(sorted(i[:2]))):i[2] for i in csv.reader(f, delimiter="\t")}
	ans = {}
	for i in l:
		ans[l[i]] = list(i)
	return json.dumps(ans)

@app.route("/temp/register", methods=["GET"])
def temp_register():
	if not auth(request.headers.get("auth")):
		return "Incorrect authorization code.", 401
	required = ["mac","temp1","temp2"]
	t = para_check(required, request)
	if not t[0]:
		return "Missing parameter [{}]".format(t[1]), 430
	data = {}
	for i in required:
		data[i] = request.args.get(i)
	with open("/var/www/flask/temp.csv", mode="r", encoding="utf-8") as f:
		l = {i[0]:{"temp1":i[1],"temp2":i[2]} for i in csv.reader(f, delimiter="\t")}
	l[data["mac"]] = {"temp1":data["temp1"],"temp2":data["temp2"]}
	output = ""
	for key in l:
		output+="{}\t{}\t{}\n".format(key,l[key]["temp1"],l[key]["temp2"])
	with open("/var/www/flask/temp.csv", mode="w", encoding="utf-8") as f:
		f.write(output)
	return temp_list()

@app.route("/temp/list", methods=["GET"])
def temp_list():
	if not auth(request.headers.get("auth")):
		return "Incorrect authorization code.", 401
	with open("/var/www/flask/temp.csv", mode="r", encoding="utf-8") as f:
		l = {i[0]:{"temp1":i[1],"temp2":i[2]} for i in csv.reader(f, delimiter="\t") if i[0]!=""}
	return json.dumps(l)

if __name__ == "__main__":
    app.run()
