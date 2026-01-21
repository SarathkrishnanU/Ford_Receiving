import requests

import random

import pickle

import os

import time

import pandas as pd

from bs4 import BeautifulSoup
 
input_file = "HELICAL.xlsx"

output_file = "HELICAL_output.xlsx"

pickle_file = "HELICAL_data_batch.pkl"

error_log_file = "HELICAL_SKU_url.txt"
 
urls = pd.read_excel(input_file)["url"].tolist()

if os.path.exists(pickle_file):

    with open(pickle_file, "rb") as f:

        records = pickle.load(f)

    processed_urls = set(rec["url"] for rec in records)

    print(f"Resuming from last saved state. URLs processed: {len(processed_urls)}")

else:

    records, processed_urls = [], set()
 
session = requests.Session()

session.headers.update({

    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'

})
 
try:

    for idx, i in enumerate(urls):

        if i in processed_urls:

            continue

        try:

            resp = session.get(i, timeout=20)

            resp.raise_for_status()

            soup = BeautifulSoup(resp.content, "html.parser")

            title = soup.title.string.strip() if soup.title else ""
 
            # --- Extract attributes as before ---

            attr_dict = {}

            for row in soup.find_all("tr"):

                cols = row.find_all("td")

                if len(cols) == 2:

                    attr_dict[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)

            for dt in soup.find_all("dt", class_="productView-info-name"):

                if dt.get_text(strip=True) == "Weight:":

                    dd = dt.find_next_sibling("dd", class_="productView-info-value")

                    if dd: attr_dict["Weight"] = dd.get_text(strip=True)

                    break
 
            # --- Extract breadcrumbs as a text string ---

            breadcrumbs_text = ""

            breadcrumbs_ul = soup.find("ul", class_="breadcrumbs")

            if breadcrumbs_ul:

                items = []

                for li in breadcrumbs_ul.find_all("li", class_="breadcrumb", recursive=False):

                    label_tag = li.find("a", class_="breadcrumb-label")

                    if label_tag:

                        label = label_tag.get_text(strip=True)

                    else:

                        label_span = li.find("span", class_="breadcrumb-label")

                        if label_span:

                            label = label_span.get_text(strip=True)

                        else:

                            label = ""

                    if label:

                        items.append(label)

                breadcrumbs_text = " > ".join(items)
 
            record = {

                "Title": title,

                "url": i,

                "Attributes": attr_dict,

                "Breadcrumbs": breadcrumbs_text

            }

            records.append(record)

            processed_urls.add(i)

            print(f"Processed: {i} ({len(records)}/{len(urls)})")

            if len(records) % 20 == 0 or idx == len(urls) - 1:

                with open(pickle_file, "wb") as f:

                    pickle.dump(records, f)

            time.sleep(random.uniform(1, 3))

        except Exception as e:

            msg = f"Failed at {i} with error: {e}\n"

            print(msg)

            with open(error_log_file, "a") as elog:

                elog.write(msg)

            time.sleep(2)

except KeyboardInterrupt:

    print("Interrupted by user, saving progress...")

    with open(pickle_file, "wb") as f:

        pickle.dump(records, f)
 
# To DataFrame and Excel

df = pd.DataFrame(records).reset_index(drop=True)

attributes_df = df["Attributes"].apply(pd.Series)

final_df = pd.concat([df[["Title", "url", "Breadcrumbs"]], attributes_df], axis=1)

final_df.to_excel(output_file, index=False)

print("Finished and saved to Excel.")