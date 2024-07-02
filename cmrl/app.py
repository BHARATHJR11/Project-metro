# app.py
from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
import io

app = Flask(__name__)

# Global variables to store DataFrames
combined_df = {}
sheet_names = []

@app.route('/', methods=['GET', 'POST'])
def index():
    global combined_df, sheet_names

    if request.method == 'POST':
        try:
            file1 = request.files['file1']
            file2 = request.files['file2']
            unique_column1 = request.form['unique_column1']
            unique_column2 = request.form['unique_column2']
            column_to_compare1 = request.form['columns_to_compare1']
            column_to_compare2 = request.form['columns_to_compare2']

            if file1 and file2:
                # Read Excel files into pandas DataFrames
                df1 = pd.read_excel(file1, dtype=str)
                df2 = pd.read_excel(file2, dtype=str)

                # Process unique columns
                df1[unique_column1] = df1[unique_column1].str.strip().str.lstrip('0')
                df2[unique_column2] = df2[unique_column2].str.strip().str.lstrip('0')

                # Set index for easy comparison
                df1.set_index(unique_column1, inplace=True)
                df2.set_index(unique_column2, inplace=True)

                # Ensure we compare only on common columns
                if column_to_compare1 not in df1.columns or column_to_compare2 not in df2.columns:
                    return "Error: No common columns found for comparison.", 400

                # Find common and unique indices
                common_index = df1.index.intersection(df2.index)
                unique_index_df1 = df1.index.difference(df2.index)

                # Compare the rows with common indices
                differing_rows = df1.loc[common_index, column_to_compare1] != df2.loc[common_index, column_to_compare2]

                # Separate the differing and identical rows
                differing_df = df1.loc[common_index][differing_rows]
                identical_df = df1.loc[common_index][~differing_rows]
                unmatched_df = df1.loc[unique_index_df1]

                # Add the unique index back to DataFrames
                differing_ = pd.DataFrame(differing_df)
                identical_ = pd.DataFrame(identical_df)
                totallyunmatched_ = pd.DataFrame(unmatched_df)
                if not differing_.empty:
                    differing_.insert(0, unique_column1, differing_.index)
                if not identical_.empty:
                    identical_.insert(0, unique_column1, identical_.index)
                if not totallyunmatched_.empty:
                    totallyunmatched_.insert(0, unique_column1, totallyunmatched_.index)

                combined_df = {
                    'Differing': differing_,
                    'Identical': identical_,
                    'TotallyUnmatched': totallyunmatched_
                }
                sheet_names = ['Differing', 'Identical', 'TotallyUnmatched']

                return render_template('index.html', sheets_available=True)

        except Exception as e:
            return f"Error: {str(e)}", 500

    return render_template('index.html', sheets_available=False)

@app.route('/get_headers', methods=['POST'])
def get_headers():
    try:
        file1 = request.files['file1']
        file2 = request.files['file2']

        headers = {}

        if file1:
            df1 = pd.read_excel(file1, dtype=str, nrows=0)
            headers['file1'] = df1.columns.tolist()
        else:
            headers['file1'] = []

        if file2:
            df2 = pd.read_excel(file2, dtype=str, nrows=0)
            headers['file2'] = df2.columns.tolist()
        else:
            headers['file2'] = []

        return jsonify(headers)

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/download')
def download():
    output = io.BytesIO()
    try:
        # Generate the combined Excel file with multiple sheets
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for sheet_name in sheet_names:
                combined_df[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)

        output.seek(0)
        return send_file(output, as_attachment=True, download_name='comparison_output.xlsx')

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)