import RoleLayout from "@/components/RoleLayout";

export default function TeacherLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RoleLayout
      allowed={["teacher", "admin"]}
      nav={[
        { label: "Courses", href: "/teacher/courses" },
        { label: "Classes", href: "/teacher/classes" },
        { label: "Interventions", href: "/teacher/interventions" },
      ]}
    >
      {children}
    </RoleLayout>
  );
}
