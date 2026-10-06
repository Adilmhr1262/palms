import RoleLayout from "@/components/RoleLayout";

export default function StudentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RoleLayout
      allowed={["student", "admin"]}
      nav={[
        { label: "My classes", href: "/student/classes" },
        { label: "Recommendations", href: "/student/recommendations" },
        { label: "Feedback", href: "/student/feedback" },
      ]}
    >
      {children}
    </RoleLayout>
  );
}
