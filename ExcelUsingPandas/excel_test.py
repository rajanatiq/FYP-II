import pandas as pd

excel_file = 'CourseDetailsCopy.xlsx'

df = pd.read_excel(excel_file)

# for index, row in df.iterrows():
#     print(f"Course Name: {row['Course Title']}")

row, columns = df.shape



class CourseAllocation():
    ID : int
    TeacherID : int
    OfferingID: int
    SECTION : int
    CourseCode: str

data = []
for i in range(row):
    data.append(df.iloc[i].to_dict())
    
courses = []

for i in data:
    new_all = CourseAllocation()
    for key, values in i.items():
        new_all.CourseCode = values
    


