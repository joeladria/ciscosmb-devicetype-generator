# ciscosmb-devicetype-generator
This set of scripts helped me generate device type definitions and images for the Catalyst 1300 series. Generated in part by ChatGPT.

These definitions are destined for the [NetBox devicetype-library](https://github.com/netbox-community/devicetype-library)

These scripts can be adapted for other models/manufacturers for bulk creation of different model series.

It consists of
* `generate.py` -- uses a predefined models.csv file to produce templates appropriate for devicetype-library
* `crop.py` -- a pillow-based cropping tool to create rear and front images based on manufacturer images
* models.csv -- input file, compiled with some help from ChatGPT based on spec pages from Cisco

Images are courtesy [Cisco Brand Exchange](https://bx.cisco.com/cisco-brand-exchange/public).