import requests

def send(mac,t1,t2):
	url = "http://api.bee3.tokyo/temp/register"
	headers = {
		"auth" : "LWwgrDhtPnwjhYw3YB7E"
	}
	payloads = {
		"mac" : mac,
		"temp1" : t1,
		"temp2" : t2
	}

	r = requests.get(url, headers=headers, params=payloads)

	return r.status_code
